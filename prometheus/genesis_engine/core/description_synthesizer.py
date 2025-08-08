# prometheus/genesis_engine/core/description_synthesizer.py

import json
from typing import List, Optional
from openai import OpenAI
import re

from prometheus.config.settings import settings
from prometheus.genesis_engine.analyzers.base import EvidenceChunk
from prometheus.genesis_engine.models import CoreDescription

# Templat prompt efisien yang telah kita rancang
PROMPT_TEMPLATE = """
You are an AI data architect. Synthesize the provided evidence into a structured JSON output.
Focus on creating a dense, factual description suitable for vector embedding and machine processing.

### ENTITY CONTEXT
- Entity Type: {entity_type}
- Entity Name: {entity_name}

### CUMULATIVE EVIDENCE
{evidence_string}

### YOUR TASK
Generate a single, raw JSON object with the following keys. No reasoning, explanations, or markdown needed.

{{
  "core_description": "A dense, factual description of the entity's functional purpose, in English. Combine all relevant clues.",
  "inferred_logic": "If any business logic is inferred from the data (e.g., from distinct values), state it here concisely. Otherwise, null.",
  "stereotype": "Classify the entity from this list: 'Master', 'Transaction', 'Junction', 'Config', 'Log', 'Detail', 'Unknown'.",
  "confidence": "A 0.0-1.0 confidence score."
}}

### JSON OUTPUT ONLY:
"""

class DescriptionSynthesizer:
    """
    Takes a collection of evidence and uses an LLM to synthesize
    a structured core description.
    """
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not found in settings.")
        self.client = OpenAI(api_key=settings.openai_api_key.get_secret_value())
        self.model = settings.synthesis_model_name

    def _build_prompt(self, entity_type: str, entity_name: str, evidence_dossier: List[EvidenceChunk]) -> str:
        """Merakit semua bagian menjadi satu prompt master."""
        evidence_blocks = []
        for chunk in evidence_dossier:
            block = f"# --- {chunk.analyzer_name} ---\n{chunk.content}"
            evidence_blocks.append(block)
        evidence_string = "\n\n".join(evidence_blocks)

        return PROMPT_TEMPLATE.format(
            entity_type=entity_type,
            entity_name=entity_name,
            evidence_string=evidence_string
        )

    def _parse_llm_response(self, response_content: str) -> dict:
        """Mengekstrak dan mem-parsing blok JSON dari respons LLM."""
        # Menggunakan regex untuk menemukan blok JSON, bahkan jika ada teks lain
        match = re.search(r'\{.*\}', response_content, re.DOTALL)
        if not match:
            raise ValueError("No valid JSON object found in the LLM response.")
        
        json_string = match.group(0)
        
        try:
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from LLM response: {e}\nResponse was: {json_string}")

    def synthesize(self, entity_type: str, entity_name: str, evidence_dossier: List[EvidenceChunk]) -> Optional[CoreDescription]:
        """
        Menjalankan proses sintesis end-to-end.
        Build prompt -> Call LLM -> Parse response -> Validate with Pydantic.
        """
        prompt = self._build_prompt(entity_type, entity_name, evidence_dossier)
        
        try:
            print(f"  > Calling LLM for {entity_name}...")
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful AI data architect that only responds with JSON."},
                    {"role": "user", "content": prompt}
                ],
                # JSON Mode memastikan output adalah JSON yang valid
                response_format={"type": "json_object"},
                temperature=0.2, # Sedikit kreativitas tapi tetap faktual
            )
            
            response_content = completion.choices[0].message.content
            if not response_content:
                print(f"⚠️ LLM returned an empty response for {entity_name}.")
                return None

            # Parse dan validasi
            parsed_data = self._parse_llm_response(response_content)
            validated_description = CoreDescription(**parsed_data)
            
            print(f"  < LLM response for {entity_name} parsed and validated successfully.")
            return validated_description

        except Exception as e:
            print(f"❌ An error occurred during LLM synthesis for {entity_name}: {e}")
            return None