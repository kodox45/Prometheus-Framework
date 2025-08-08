# prometheus/genesis_engine/analyzers/stock/schema_analyzer.py

from typing import Optional
from prometheus.genesis_engine.analyzers.base import BaseAnalyzer, NodeContext, EvidenceChunk
from prometheus.genesis_engine.models import TableSchema, ColumnSchema

class SchemaDetailAnalyzer(BaseAnalyzer):
    """
    Mengekstrak informasi struktural dasar langsung dari objek skema
    yang sudah diekstrak, tanpa melakukan query baru ke database.
    """
    @property
    def name(self) -> str:
        return "SchemaDetail"

    def analyze(self, context: NodeContext) -> Optional[EvidenceChunk]:
        if context.node_type == "Table":
            return self._analyze_table(context)
        elif context.node_type == "Column":
            return self._analyze_column(context)
        return None

    def _find_table_schema(self, table_name: str, context: NodeContext) -> Optional[TableSchema]:
        """Helper untuk menemukan objek TableSchema dari nama tabel."""
        return next((t for t in context.db_schema.tables if t.table_name == table_name), None)

    def _analyze_table(self, context: NodeContext) -> Optional[EvidenceChunk]:
        table_schema = self._find_table_schema(context.node_name, context)
        if not table_schema:
            return None

        content_lines = [
            f"primary_key: {table_schema.primary_key}",
            f"column_count: {len(table_schema.columns)}",
            f"foreign_key_count: {len(table_schema.foreign_keys)}",
            f"is_junction_table: {table_schema.is_junction_table}"
        ]
        return EvidenceChunk(
            analyzer_name=self.name,
            content="\n".join(content_lines)
        )

    def _analyze_column(self, context: NodeContext) -> Optional[EvidenceChunk]:
        table_name, column_name = context.node_name.split('.', 1)
        table_schema = self._find_table_schema(table_name, context)
        if not table_schema:
            return None
        
        column_schema = next((c for c in table_schema.columns if c.name == column_name), None)
        if not column_schema:
            return None

        content_lines = [
            f"data_type: {column_schema.data_type}",
            f"is_nullable: {column_schema.is_nullable}",
            f"is_primary_key: {column_name in table_schema.primary_key}",
        ]
        if column_schema.comment:
            content_lines.append(f"db_comment: '{column_schema.comment}'")
        
        return EvidenceChunk(
            analyzer_name=self.name,
            content="\n".join(content_lines)
        )