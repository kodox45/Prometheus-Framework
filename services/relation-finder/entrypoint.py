import argparse
import json
from google.cloud import storage

from prometheus.config.settings import settings
from prometheus.connectors.neo4j_connector import Neo4jConnector
from prometheus.genesis_engine.core.implicit_relation_finder import ImplicitRelationFinder
from prometheus.genesis_engine.loader import SchemaLoader


def read_gcs_json(uri: str) -> dict:
    if not uri or not uri.startswith("gs://"):
        return {}
    _, path = uri.split("gs://", 1)
    bucket, blob = path.split("/", 1)
    client = storage.Client()
    data = client.bucket(bucket).blob(blob).download_as_text()
    return json.loads(data)


def main():
    parser = argparse.ArgumentParser(description="Relation-finder service entrypoint")
    parser.add_argument("--payload-gcs", required=False)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-similarity", type=float, default=0.8)
    parser.add_argument("--min-confidence", type=float, default=0.85)
    args = parser.parse_args()

    if args.payload_gcs:
        _ = read_gcs_json(args.payload_gcs)

    neo = Neo4jConnector(settings)
    loader = SchemaLoader(neo)
    finder = ImplicitRelationFinder(neo4j_connector=neo, relation_creation_fn=loader.create_implicit_relation)
    finder.find_and_create_relations(
        top_k=args.top_k,
        min_similarity_score=args.min_similarity,
        min_llm_confidence=args.min_confidence,
    )
    print("✅ Relation discovery finished")


if __name__ == "__main__":
    main()


