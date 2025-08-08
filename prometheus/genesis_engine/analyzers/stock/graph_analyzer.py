# prometheus/genesis_engine/analyzers/stock/graph_analyzer.py

from typing import Optional, List
from prometheus.genesis_engine.analyzers.base import BaseAnalyzer, NodeContext, EvidenceChunk
from prometheus.connectors.neo4j_connector import Neo4jConnector

class KnowledgeGraphAnalyzer(BaseAnalyzer):
    """
    Menganalisis tetangga sebuah node (Tabel atau Kolom) di dalam Knowledge Graph
    untuk menemukan informasi relasional yang sudah dipetakan.
    """
    def __init__(self, neo4j_connector: Neo4jConnector):
        self.connector = neo4j_connector

    @property
    def name(self) -> str:
        return "KnowledgeGraphContext"

    def analyze(self, context: NodeContext) -> Optional[EvidenceChunk]:
        try:
            with self.connector.get_session() as session:
                if context.node_type == "Table":
                    clues = self._analyze_table(session, context.node_name)
                elif context.node_type == "Column":
                    clues = self._analyze_column(session, context.node_name)
                else:
                    return None
        except Exception as e:
            print(f"⚠️ Error in KnowledgeGraphAnalyzer for {context.node_name}: {e}")
            return None

        if not clues:
            return None

        return EvidenceChunk(
            analyzer_name=self.name,
            content="\n".join(clues)
        )

    def _analyze_table(self, session, table_name: str) -> List[str]:
        """Menganalisis relasi untuk node Tabel."""
        clues = []
        # Query untuk relasi keluar (outgoing)
        out_query = """
        MATCH (t:Table {name: $table_name})-[r:EXPLICIT_FK_TO]->(target:Table)
        RETURN target.name AS target_table, r.on_delete AS on_delete
        """
        out_results = session.run(out_query, table_name=table_name).data()
        for res in out_results:
            rule = f" (on_delete: {res['on_delete']})" if res.get('on_delete') else ""
            clues.append(f"relation_out: {res['target_table']}{rule}")

        # Query untuk relasi masuk (incoming)
        in_query = """
        MATCH (source:Table)-[r:EXPLICIT_FK_TO]->(t:Table {name: $table_name})
        RETURN source.name AS source_table
        """
        in_results = session.run(in_query, table_name=table_name).data()
        if in_results:
            source_tables = [res['source_table'] for res in in_results]
            clues.append(f"relation_in: {source_tables[:5]}")
            
        return clues

    def _analyze_column(self, session, column_full_name: str) -> List[str]:
        """Menganalisis relasi untuk node Kolom."""
        clues = []
        try:
            table_name, column_name = column_full_name.split('.', 1)
        except ValueError:
            return []

        # Cari tahu apakah kolom ini adalah bagian dari suatu Foreign Key
        fk_query = """
        MATCH (t:Table {name: $table_name})-[r:EXPLICIT_FK_TO]->(target:Table)
        WHERE $column_name IN r.constrained_columns
        RETURN target.name AS target_table, 
               r.constrained_columns AS source_columns, 
               r.referred_columns AS target_columns
        """
        fk_results = session.run(fk_query, table_name=table_name, column_name=column_name).data()
        
        for res in fk_results:
            try:
                source_idx = res['source_columns'].index(column_name)
                target_column = res['target_columns'][source_idx]
                clues.append(f"fk_to: {res['target_table']}.{target_column}")
            except (ValueError, IndexError, KeyError):
                 clues.append(f"fk_to: {res['target_table']}")
                
        return clues