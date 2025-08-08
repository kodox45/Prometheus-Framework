# prometheus/genesis_engine/core/cost_calculator.py

from typing import List, Dict
from prometheus.genesis_engine.analyzers.base import EvidenceChunk
from prometheus.genesis_engine.core.description_synthesizer import PROMPT_TEMPLATE
from prometheus.config.settings import settings
# Kita akan menggunakan tokenizer dari OpenAI untuk perhitungan yang akurat
import tiktoken

class EnrichmentCostCalculator:
    """
    Estimates the financial cost of the enrichment phase based on
    token counts and configured model prices.
    """
    def __init__(self):
        # Inisialisasi tokenizer. "cl100k_base" adalah yang digunakan oleh model GPT-3.5/4.
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            # Fallback jika tokenizer tidak bisa dimuat
            self.tokenizer = None
        
        # Harga per 1 token (bukan per 1 juta)
        self.price_per_input_token = settings.synthesis_price_input_usd_per_mtkn / 1_000_000
        self.price_per_output_token = settings.synthesis_price_output_usd_per_mtkn / 1_000_000

        # Estimasi token dari komponen prompt yang statis
        self.static_prompt_template_tokens = self._count_tokens(PROMPT_TEMPLATE)
        
        # Estimasi token output yang konservatif (berdasarkan pengalaman kita)
        self.estimated_output_tokens_per_entity = 120

    def _count_tokens(self, text: str) -> int:
        """Menghitung jumlah token dalam sebuah string menggunakan tiktoken."""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Fallback sederhana jika tiktoken gagal: 1 token ~ 4 karakter
            return len(text) // 4

    def estimate_cost(self, all_entities: List[tuple], evidence_map: Dict[str, List[EvidenceChunk]]) -> Dict:
        """
        Menghitung estimasi biaya total untuk semua entitas yang akan diproses.

        Args:
            all_entities: List dari tuple (entity_type, entity_name).
            evidence_map: Dictionary yang memetakan entity_name ke daftar EvidenceChunk-nya.

        Returns:
            Sebuah dictionary berisi laporan biaya.
        """
        total_input_tokens = 0
        total_output_tokens = 0
        entity_count = len(all_entities)

        for entity_type, entity_name in all_entities:
            # 1. Hitung token input
            input_tokens_for_entity = self.static_prompt_template_tokens
            
            # Tambahkan token dari nama entitas
            input_tokens_for_entity += self._count_tokens(f"- Entity Type: {entity_type}\n- Entity Name: {entity_name}")

            # Tambahkan token dari dossier bukti
            evidence_dossier = evidence_map.get(entity_name, [])
            evidence_string = "\n\n".join([f"# --- {c.analyzer_name} ---\n{c.content}" for c in evidence_dossier])
            input_tokens_for_entity += self._count_tokens(evidence_string)
            
            total_input_tokens += input_tokens_for_entity

            # 2. Hitung token output
            total_output_tokens += self.estimated_output_tokens_per_entity
        
        # 3. Hitung biaya
        total_input_cost = total_input_tokens * self.price_per_input_token
        total_output_cost = total_output_tokens * self.price_per_output_token
        total_cost = total_input_cost + total_output_cost

        return {
            "model_name": settings.synthesis_model_name,
            "entity_count": entity_count,
            "estimated_input_tokens": total_input_tokens,
            "estimated_output_tokens": total_output_tokens,
            "estimated_total_tokens": total_input_tokens + total_output_tokens,
            "input_cost_usd": f"${total_input_cost:.4f}",
            "output_cost_usd": f"${total_output_cost:.4f}",
            "total_estimated_cost_usd": f"${total_cost:.2f}"
        }
    
class RelationCostCalculator:
    """
    Tracks and estimates the cost of the implicit relation finding phase.
    """
    def __init__(self):
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None
        
        # Gunakan harga dari settings
        self.price_per_input_token = settings.relation_price_input_usd_per_mtkn / 1_000_000
        self.price_per_output_token = settings.relation_price_output_usd_per_mtkn / 1_000_000
        
        # Lacak penggunaan aktual
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_verification_calls = 0

    def _count_tokens(self, text: str) -> int:
        """Menghitung jumlah token dalam sebuah string."""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        return len(text) // 4
    
    def track_call(self, prompt_tokens: int, completion_tokens: int):
        """Mencatat penggunaan token dari satu panggilan verifikasi LLM."""
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_verification_calls += 1

    def get_total_cost(self) -> float:
        """Menghitung total biaya aktual."""
        input_cost = self.total_prompt_tokens * self.price_per_input_token
        output_cost = self.total_completion_tokens * self.price_per_output_token
        return input_cost + output_cost

    def generate_report(self) -> str:
        """Menghasilkan laporan biaya aktual."""
        if self.total_verification_calls == 0:
            return "Relation Cost Report: No LLM verification calls were made."

        report_lines = [
            "--- Implicit Relation LLM Cost Report ---",
            f"Total Verification Calls: {self.total_verification_calls}",
            f"Total Input Tokens: {self.total_prompt_tokens:,}",
            f"Total Output Tokens: {self.total_completion_tokens:,}",
            f"TOTAL COST: ${self.get_total_cost():.4f}",
            "------------------------------------------"
        ]
        return "\n".join(report_lines)