import argparse

from prometheus.config.settings import settings
from prometheus.connectors.postgres_connector import PostgresConnector
from prometheus.connectors.neo4j_connector import Neo4jConnector
from prometheus.genesis_engine.orchestrator import Orchestrator

def main():
    parser = argparse.ArgumentParser(description="Run Genesis Engine enrichment PoC")
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--clean-db", action="store_true", help="Wipe Neo4j before loading schema")
    parser.add_argument("--force-rerun-enrichment", action="store_true")
    args = parser.parse_args()

    pg_connector = PostgresConnector(settings)
    neo4j_connector = Neo4jConnector(settings)

    orchestrator = Orchestrator(pg_connector, neo4j_connector)
    orchestrator.run_genesis(
        sample_size=args.sample_size,
        clean_db=args.clean_db,
        force_rerun_enrichment=args.force_rerun_enrichment
    )

if __name__ == "__main__":
    main()