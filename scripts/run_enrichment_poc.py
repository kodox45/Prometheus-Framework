# scripts/run_enrichment_poc.

print("--- DEBUGGING: VERIFYING SETTINGS ---")
from prometheus.config.settings import settings
print(f"NEO4J_URI being used: {settings.neo4j_uri}")
print(f"Is NEO4J_URI correct? {settings.neo4j_uri == 'bolt://localhost:7687'}")
if not settings.neo4j_uri == 'bolt://localhost:7687':
    print("!!!!!! WARNING: NEO4J_URI IS INCORRECT. CHECK YOUR ENVIRONMENT. !!!!!!")
    exit() # Hentikan eksekusi jika salah
print("--- DEBUGGING END ---")

from prometheus.config.settings import settings
from prometheus.connectors.postgres_connector import PostgresConnector
from prometheus.connectors.neo4j_connector import Neo4jConnector
from prometheus.genesis_engine.orchestrator import Orchestrator

def main():
    pg_connector = PostgresConnector(settings)
    neo4j_connector = Neo4jConnector(settings)
    
    orchestrator = Orchestrator(pg_connector, neo4j_connector)
    orchestrator.run_genesis(sample_size=20, clean_db=False, force_rerun_enrichment=False)

if __name__ == "__main__":
    main()