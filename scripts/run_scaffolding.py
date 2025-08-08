# scripts/run_scaffolding.py

from prometheus.config.settings import settings
from prometheus.connectors.postgres_connector import PostgresConnector
from prometheus.connectors.neo4j_connector import Neo4jConnector
from prometheus.genesis_engine.extractor import SchemaExtractor
from prometheus.genesis_engine.loader import SchemaLoader

def main():
    print("--- Running Genesis Engine: Structural Scaffolding ---")

    # Menggunakan 'with' untuk setiap konektor
    with PostgresConnector(settings) as pg_connector, \
         Neo4jConnector(settings) as neo4j_connector:

        # 1. Ekstrak Skema dari PostgreSQL
        print("\n[Phase 1/2] Extracting schema from PostgreSQL...")
        extractor = SchemaExtractor(pg_connector)
        db_schema = extractor.extract_schema(schema_name="public")
        print(f"Extraction complete. Found {len(db_schema.tables)} tables.")

        # 2. Muat Skema ke Neo4j
        print("\n[Phase 2/2] Loading schema into Neo4j...")
        loader = SchemaLoader(neo4j_connector)
        # clean_db=True akan menghapus DB Neo4j sebelum memuat. Hati-hati!
        loader.load_schema(db_schema, clean_db=True)
        print("Loading complete.")

    print("\n🎉 --- Structural Scaffolding Finished Successfully! --- 🎉")
    print("Go check your Neo4j Browser to see the graph!")

if __name__ == "__main__":
    main()