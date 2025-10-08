import argparse
import json
from typing import Optional
from google.cloud import storage

from prometheus.config.settings import settings
from prometheus.connectors.postgres_connector import PostgresConnector
from prometheus.genesis_engine.extractor import SchemaExtractor


def read_gcs_json(uri: str) -> dict:
    if not uri or not uri.startswith("gs://"):
        return {}
    _, path = uri.split("gs://", 1)
    bucket, blob = path.split("/", 1)
    client = storage.Client()
    data = client.bucket(bucket).blob(blob).download_as_text()
    return json.loads(data)


def write_gcs_json(uri: str, data: dict) -> None:
    _, path = uri.split("gs://", 1)
    bucket, blob = path.split("/", 1)
    client = storage.Client()
    storage.Blob(blob, client.bucket(bucket)).upload_from_string(
        json.dumps(data), content_type="application/json"
    )


def main():
    parser = argparse.ArgumentParser(description="Extractor service entrypoint")
    parser.add_argument("--payload-gcs", required=False)
    parser.add_argument("--schema-name", default="public")
    parser.add_argument("--output-gcs", required=False, help="gs://bucket/path/schema.json")
    args = parser.parse_args()

    # Optional payload for future use
    if args.payload_gcs:
        _ = read_gcs_json(args.payload_gcs)

    pg = PostgresConnector(settings)
    extractor = SchemaExtractor(pg)
    db_schema = extractor.extract_schema(schema_name=args.schema_name)

    if args.output_gcs:
        # Pydantic v2 supports .dict(); keep consistent with existing codebase
        data = {"tables": [t.dict() for t in db_schema.tables]}
        write_gcs_json(args.output_gcs, data)
        print(f"✅ Wrote extracted schema to {args.output_gcs}")
    else:
        print("✅ Extraction finished (no output path provided)")


if __name__ == "__main__":
    main()


