from __future__ import annotations

import json

from prometheus.config.settings import settings
from prometheus.genesis_engine.core.embedding_generator import EmbeddingGenerator
from prometheus.genesis_engine.core.description_synthesizer import DescriptionSynthesizer
from prometheus.genesis_engine.analyzers.base import EvidenceChunk


def main() -> None:
    print("--- Verifying Gemini integration (framework) ---")
    print(f"GOOGLE_API_KEY configured: {settings.google_api_key is not None}")
    print(f"SYNTHESIS_MODEL_NAME: {settings.synthesis_model_name}")

    # 1) Test LLM synthesis (JSON mode)
    try:
        synth = DescriptionSynthesizer()
        evidence = [
            EvidenceChunk(
                analyzer_name="TestAnalyzer",
                content=(
                    "Table res_partner appears to represent business partners, including customers and vendors. "
                    "It includes fields like name, email, and address, and is often linked to sales orders."
                ),
            )
        ]
        result = synth.synthesize("Table", "res_partner", evidence)
        if result:
            print("LLM synthesis OK. Parsed CoreDescription:")
            print(result.model_dump_json(indent=2))
        else:
            print("LLM synthesis returned None")
    except Exception as exc:
        print("LLM synthesis FAILED:")
        print(repr(exc))

    # 2) Test embeddings
    try:
        embedder = EmbeddingGenerator()
        vec = embedder.generate("Hello from Gemini embeddings")
        if vec:
            print(f"Embedding OK. Length: {len(vec)}. First 5 values: {json.dumps(vec[:5])}")
        else:
            print("Embedding returned None")
    except Exception as exc:
        print("Embedding generation FAILED:")
        print(repr(exc))


if __name__ == "__main__":
    main()


