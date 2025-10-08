import argparse
import json
from typing import List
from google.cloud import storage

from prometheus.genesis_engine.core.description_synthesizer import DescriptionSynthesizer
from prometheus.genesis_engine.analyzers.base import EvidenceChunk


def read_gcs_json(uri: str) -> dict:
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
    parser = argparse.ArgumentParser(description="Synthesizer service entrypoint")
    parser.add_argument("--input-gcs", required=True, help="gs://bucket/path/evidence.json")
    parser.add_argument("--entity-type", required=True)
    parser.add_argument("--entity-name", required=True)
    parser.add_argument("--output-gcs", required=True, help="gs://bucket/path/desc.json")
    args = parser.parse_args()

    data = read_gcs_json(args.input_gcs)
    evidence_list = [EvidenceChunk(**chunk) for chunk in data.get("evidence", [])]

    synth = DescriptionSynthesizer()
    core_desc = synth.synthesize(args.entity_type, args.entity_name, evidence_list)

    result = core_desc.dict() if core_desc else {"error": "synthesis_failed"}
    write_gcs_json(args.output_gcs, result)
    print(f"✅ Wrote core description to {args.output_gcs}")


if __name__ == "__main__":
    main()


