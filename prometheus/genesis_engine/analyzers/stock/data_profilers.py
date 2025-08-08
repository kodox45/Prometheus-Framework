# prometheus/genesis_engine/analyzers/stock/data_profilers.py

from typing import Optional, List
from sqlalchemy import text
from prometheus.genesis_engine.analyzers.base import BaseAnalyzer, NodeContext, EvidenceChunk

class SmartDataProfilerAnalyzer(BaseAnalyzer):
    # --- AMBANG BATAS BARU YANG LEBIH CERDAS ---
    MINIMUM_ROWS_FOR_ANALYSIS = 50  # Jangan repot-repot menganalisis tabel yang terlalu kecil
    MAX_DISTINCT_VALUES = 30        # Batas atas absolut untuk nilai unik
    MAX_DISTINCT_RATIO = 0.1        # Nilai unik harus kurang dari 10% total baris

    @property
    def name(self) -> str:
        return "DataProfile"

    def analyze(self, context: NodeContext) -> Optional[EvidenceChunk]:
        if context.node_type != "Column":
            return None

        try:
            table_name, column_name = context.node_name.split('.', 1)
            
            with context.db_connector.engine.connect() as connection:
                
                # --- QUERY BARU: Dapatkan semua statistik dalam satu kali jalan ---
                stats_query = text(f"""
                SELECT
                    COUNT(*) AS total_rows,
                    COUNT(DISTINCT "{column_name}") AS distinct_count
                FROM public."{table_name}"
                """)
                
                try:
                    stats_result = connection.execute(stats_query).mappings().one()
                    total_rows = stats_result['total_rows']
                    distinct_count = stats_result['distinct_count']
                except Exception:
                    # Gagal pada tipe data yang tidak mendukung DISTINCT (misalnya, JSONB)
                    return self._fetch_random_samples(connection, table_name, column_name) # type: ignore

                # --- LOGIKA PENYARINGAN BARU ---
                is_likely_categorical = False
                if total_rows >= self.MINIMUM_ROWS_FOR_ANALYSIS and distinct_count < self.MAX_DISTINCT_VALUES:
                    distinct_ratio = distinct_count / total_rows if total_rows > 0 else 0
                    if distinct_ratio < self.MAX_DISTINCT_RATIO:
                        is_likely_categorical = True

                # --- Ambil sampel & nilai unik berdasarkan hasil ---
                random_samples = self._fetch_random_samples(connection, table_name, column_name, return_content=False)
                distinct_values = None
                if is_likely_categorical:
                    values_query = text(f'SELECT DISTINCT "{column_name}" FROM public."{table_name}" WHERE "{column_name}" IS NOT NULL LIMIT {self.MAX_DISTINCT_VALUES}')
                    values_result = connection.execute(values_query).fetchall()
                    distinct_values = sorted([str(row[0]) for row in values_result])

                # --- Rakit Bukti ---
                return self._build_evidence_chunk(random_samples, distinct_values)
                
        except Exception as e:
            print(f"⚠️  Major error in SmartDataProfilerAnalyzer for {context.node_name}: {e}")
            return None

    def _fetch_random_samples(self, connection, table_name, column_name, return_content=True):
        """Helper untuk mengambil sampel acak."""
        try:
            query = text(f'SELECT "{column_name}" FROM public."{table_name}" WHERE "{column_name}" IS NOT NULL ORDER BY random() LIMIT 5')
            result = connection.execute(query).fetchall()
            samples = [str(row[0]) for row in result]
            if return_content: # Jika dipanggil sebagai fallback
                return self._build_evidence_chunk(samples, None)
            return samples
        except Exception:
            return []

    def _build_evidence_chunk(self, samples, distincts):
        """Helper untuk merakit EvidenceChunk."""
        content_lines = []
        if samples:
            content_lines.append(f"sample_values: {samples}")
        
        if distincts:
            content_lines.append(f"cardinality_type: LOW_RELATIVE")
            content_lines.append(f"distinct_values: {distincts}")
        
        if not content_lines:
            content_lines.append("sample_values: [] # Column is likely empty or contains only NULLs.")
        
        return EvidenceChunk(analyzer_name=self.name, content="\n".join(content_lines))