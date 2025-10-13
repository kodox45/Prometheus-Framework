# prometheus/genesis_engine/core/embedding_generator.py

from typing import List, Optional
from google import genai

from prometheus.config.settings import settings

class EmbeddingGenerator:
    """
    Generates vector embeddings for text using Google's Generative AI API.
    """
    EMBEDDING_MODEL = "gemini-embedding-001"
    EMBEDDING_DIMENSIONS = 1536

    def __init__(self):
        # Support either direct Generative AI API via API key or Vertex AI via ADC
        if settings.use_vertex_ai:
            if not settings.gcp_project_id or not settings.gcp_location:
                raise ValueError("Vertex AI enabled but gcp_project_id or gcp_location is not set in settings.")
            self._client = genai.Client(
                vertexai=True,
                project=settings.gcp_project_id,
                location=settings.gcp_location,
            )
        else:
            if not settings.google_api_key:
                raise ValueError("Google API key not found in settings.")
            self._client = genai.Client(api_key=settings.google_api_key.get_secret_value())
        print(f"EmbeddingGenerator initialized with model: {self.EMBEDDING_MODEL}")

    def generate(self, text: str) -> Optional[List[float]]:
        """
        Generates a vector embedding for a single string of text.

        Args:
            text: The input text to be embedded.

        Returns:
            A list of floats representing the vector, or None if an error occurs.
        """
        if not text or not isinstance(text, str):
            return None
            
        try:
            # Ganti newline dengan spasi untuk hasil embedding yang lebih baik
            text_to_embed = text.replace("\n", " ")
            
            # Panggil API Embeddings (google-genai)
            response = self._client.models.embed_content(
                model=self.EMBEDDING_MODEL,
                contents=text_to_embed,
                config={
                    "output_dimensionality": self.EMBEDDING_DIMENSIONS
                },
            )

            # Ekstrak embedding dari respons (google-genai returns `embeddings`)
            embedding_vector = None
            embeddings_obj = getattr(response, "embeddings", None)
            if embeddings_obj is None and isinstance(response, dict):
                embeddings_obj = response.get("embeddings")
            if embeddings_obj is not None:
                if isinstance(embeddings_obj, list) and len(embeddings_obj) > 0:
                    first = embeddings_obj[0]
                    if hasattr(first, "values"):
                        embedding_vector = list(first.values)  # type: ignore
                    elif isinstance(first, dict) and "values" in first:
                        embedding_vector = first["values"]  # type: ignore
                    elif isinstance(first, list):
                        embedding_vector = first  # type: ignore
            if embedding_vector is None:
                # Fallback to older shape
                embedding_vector = getattr(response, "embedding", None)
                if embedding_vector is None and isinstance(response, dict):
                    embedding_vector = response.get("embedding")
            
            # Verifikasi dimensi untuk keamanan
            if len(embedding_vector) != self.EMBEDDING_DIMENSIONS:
                print(f"⚠️ Warning: Embedding dimension mismatch. Expected {self.EMBEDDING_DIMENSIONS}, got {len(embedding_vector)}.")
                return None
            
            return embedding_vector

        except Exception as e:
            print(f"Error during embedding generation: {e}")
            return None