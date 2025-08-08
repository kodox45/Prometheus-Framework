# prometheus/genesis_engine/loader.py

from prometheus.connectors.neo4j_connector import Neo4jConnector
from prometheus.genesis_engine.models import DatabaseSchema, CoreDescription
from neo4j.exceptions import Neo4jError
from typing import List, Optional
from prometheus.genesis_engine.core.embedding_generator import EmbeddingGenerator
from prometheus.genesis_engine.models import ImplicitRelation

class SchemaLoader:
    """
    Loads a structured DatabaseSchema object into a Neo4j knowledge graph,
    creating the initial structural scaffold.
    """

    def __init__(self, connector: Neo4jConnector):
        """
        Initializes the loader with a Neo4j connector.

        Args:
            connector: An instance of Neo4jConnector.
        """
        self.connector = connector

    def _clear_database(self):
        """Wipes the entire Neo4j database. Use with caution."""
        print("🔥 Wiping entire Neo4j database...")
        with self.connector.get_session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("✅ Database wiped clean.")

    def load_schema(self, db_schema: DatabaseSchema, clean_db: bool = True):
        """
        Loads the entire database schema into Neo4j.

        Args:
            db_schema: The DatabaseSchema object from the Extractor.
            clean_db: If True, the Neo4j database will be wiped before loading.
        """
        self.connector.connect()

        if clean_db:
            self._clear_database()

        print("🚀 Starting to load database schema into Neo4j...")
        try:
            with self.connector.get_session() as session:
                # --- Step 1: Create all Table and Column nodes in one go ---
                self._create_all_nodes(session, db_schema)

                # --- Step 2: Create all HAS_COLUMN relationships ---
                self._create_has_column_relationships(session, db_schema)

                # --- Step 3: Create all EXPLICIT_FK_TO relationships ---
                self._create_fk_relationships(session, db_schema)
        
        except Neo4jError as e:
            print(f"❌ A Neo4j error occurred: {e}")
            raise
        
        print("✅ Structural scaffold of the knowledge graph loaded successfully.")

    def _create_all_nodes(self, session, db_schema: DatabaseSchema):
        """Creates all Table and Column nodes efficiently."""
        print("  - Creating all :Table and :Column nodes...")
        # This query uses UNWIND to process a list of tables and their columns
        # It's much more efficient than running one query per table/column.
        query = """
        UNWIND $tables as table_data
        MERGE (t:Table {name: table_data.table_name})
        SET t.schema = table_data.schema_name,
            t.comment = table_data.comment,
            t.primary_key = table_data.primary_key,
            t.unique_constraints = [uc IN table_data.unique_constraints | uc.name],
            t.indexes = [idx IN table_data.indexes | idx.name]
        
        FOREACH (ignoreMe IN CASE WHEN table_data.is_junction_table THEN [1] ELSE [] END |
          SET t:JunctionTable
        )
            
        WITH t, table_data.columns as columns, table_data.primary_key as pk_cols
        UNWIND columns as column_data
        MERGE (c:Column {name: t.name + '.' + column_data.name})
        SET c.table_name = t.name,
            c.data_type = column_data.data_type,
            c.is_nullable = column_data.is_nullable,
            c.comment = column_data.comment,
            c.is_primary_key = (column_data.name IN pk_cols)
        """
        # We need to convert our Pydantic models to dictionaries for the driver
        tables_dict = [table.dict() for table in db_schema.tables]
        session.run(query, tables=tables_dict)

    def _create_has_column_relationships(self, session, db_schema: DatabaseSchema):
        """Creates [:HAS_COLUMN] relationships from Tables to their Columns."""
        print("  - Creating [:HAS_COLUMN] relationships...")
        query = """
        MATCH (t:Table), (c:Column)
        WHERE c.name STARTS WITH t.name + '.'
        MERGE (t)-[:HAS_COLUMN]->(c)
        """
        session.run(query)

    def _create_fk_relationships(self, session, db_schema: DatabaseSchema):
        """Creates [:EXPLICIT_FK_TO] relationships between Table nodes."""
        print("  - Creating [:EXPLICIT_FK_TO] relationships...")
        # We process only tables that have foreign keys
        tables_with_fks = [table for table in db_schema.tables if table.foreign_keys]
        
        query = """
        UNWIND $tables_data as table_data
        MATCH (source_table:Table {name: table_data.table_name})
        
        UNWIND table_data.foreign_keys as fk_data
        MATCH (target_table:Table {name: fk_data.referred_table})
        
        MERGE (source_table)-[r:EXPLICIT_FK_TO]->(target_table)
        ON CREATE SET
          r.constrained_columns = fk_data.constrained_columns,
          r.referred_columns = fk_data.referred_columns,
          r.on_update = fk_data.on_update,
          r.on_delete = fk_data.on_delete
        ON MATCH SET
          r.on_update = fk_data.on_update,
          r.on_delete = fk_data.on_delete
        """
        tables_dict = [table.dict() for table in tables_with_fks]
        session.run(query, tables_data=tables_dict)

    def update_node_enrichment(self, node_type: str, node_name: str,
                               description: CoreDescription,
                               embedding: Optional[List[float]]):
        """
        Updates an existing node in the KG with its semantic properties.

        Args:
            node_type: "Table" or "Column".
            node_name: The unique name of the node (e.g., "res_users" or "res_users.id").
            description: The CoreDescription object from the synthesizer.
            embedding: The vector embedding list of floats.
        """
        # Kita menggunakan f-string untuk label karena Cypher tidak mendukung
        # parameterisasi label node secara langsung. Ini aman karena input kita terkontrol.
        query = f"""
        MATCH (n:{node_type} {{name: $node_name}})
        SET n += $properties, 
            n.embedding = $embedding,
            n.is_enriched = true,
            n.last_enriched_at = timestamp()
        """
        
        # Buat dictionary properti dari objek Pydantic
        properties = description.dict()
        
        try:
            with self.connector.get_session() as session:
                session.run(query, node_name=node_name, properties=properties, embedding=embedding) # type: ignore
        except Neo4jError as e:
            print(f"❌ Failed to update node {node_name}: {e}")
            
    # --- METODE BARU UNTUK INDEKS VEKTOR ---
    def create_vector_index(self):
        """
        Creates separate, compatible vector indexes for Table and Column nodes.
        """
        print("🚀 Creating compatible vector indexes...")
        from prometheus.genesis_engine.core.embedding_generator import EmbeddingGenerator
        
        # Nama indeks yang berbeda untuk setiap label
        table_index_name = "table_embeddings"
        column_index_name = "column_embeddings"
        
        query_table = f"""
        CREATE VECTOR INDEX {table_index_name} IF NOT EXISTS
        FOR (n:Table) ON (n.embedding)
        OPTIONS {{ indexConfig: {{ `vector.dimensions`: {EmbeddingGenerator.EMBEDDING_DIMENSIONS}, `vector.similarity_function`: 'cosine' }} }}
        """
        
        query_column = f"""
        CREATE VECTOR INDEX {column_index_name} IF NOT EXISTS
        FOR (n:Column) ON (n.embedding)
        OPTIONS {{ indexConfig: {{ `vector.dimensions`: {EmbeddingGenerator.EMBEDDING_DIMENSIONS}, `vector.similarity_function`: 'cosine' }} }}
        """
        
        try:
            with self.connector.get_session() as session:
                print(f"  - Creating index '{table_index_name}' for :Table nodes...")
                session.run(query_table) # type: ignore
                print(f"  - Creating index '{column_index_name}' for :Column nodes...")
                session.run(query_column) # type: ignore
            print("✅ Vector indexes created successfully.")
        except Neo4jError as e:
            print(f"❌ Could not create vector index. Ensure Neo4j Enterprise is running. Error: {e}")


    def create_implicit_relation(self, source_table_name: str, target_table_name: str, details: ImplicitRelation):
        """Creates an [:IMPLICIT_RELATION_TO] between two tables."""
        query = """
        MATCH (a:Table {name: $source_name})
        MATCH (b:Table {name: $target_name})
        MERGE (a)-[r:IMPLICIT_RELATION_TO]->(b)
        SET r.type = $rel_type,
            r.llm_justification = $justification,
            r.llm_confidence = $confidence
        """
        try:
            with self.connector.get_session() as session:
                session.run(query,
                            source_name=source_table_name,
                            target_name=target_table_name,
                            rel_type=details.relationship_type or 'RELATED_TO', # Fallback jika LLM tidak memberikan tipe
                            justification=details.justification,
                            confidence=details.confidence_score
                           )
        except Neo4jError as e:
            print(f"❌ Failed to create implicit relation between {source_table_name} and {target_table_name}: {e}")