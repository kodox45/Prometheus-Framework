import argparse
import json
import os
from google.cloud import storage

from prometheus.config.settings import settings
from prometheus.connectors.postgres_connector import PostgresConnector
from prometheus.connectors.neo4j_connector import Neo4jConnector
from prometheus.genesis_engine.orchestrator import Orchestrator


def read_gcs_json(uri: str) -> dict:
    if not uri.startswith("gs://"):
        return json.loads(uri)
    _, path = uri.split("gs://", 1)
    bucket, blob = path.split("/", 1)
    client = storage.Client()
    data = client.bucket(bucket).blob(blob).download_as_text()
    return json.loads(data)


def main():
    parser = argparse.ArgumentParser(description="Cloud Run runner entrypoint")
    parser.add_argument("--payload-gcs", required=False, help="gs://bucket/path.json or inline JSON")
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--clean-db", action="store_true")
    parser.add_argument("--force-rerun-enrichment", action="store_true")
    args = parser.parse_args()

    # Optional: read payload for future per-customer config (not used directly yet)
    if args.payload_gcs:
        try:
            payload = read_gcs_json(args.payload_gcs)
            os.environ.setdefault("ASSUME_YES", "true")
        except Exception as e:
            print(f"⚠️ Could not read payload: {e}")

    pg_connector = PostgresConnector(settings)
    neo4j_connector = Neo4jConnector(settings)

    orchestrator = Orchestrator(pg_connector, neo4j_connector)
    orchestrator.run_genesis(
        sample_size=args.sample_size,
        clean_db=args.clean_db,
        force_rerun_enrichment=args.force_rerun_enrichment,
    )


if __name__ == "__main__":
    main()


