# prometheus/genesis_engine/core/embedding_generator.py

from typing import List, Optional
from openai import OpenAI

from prometheus.config.settings import settings

class EmbeddingGenerator:
    """
    Generates vector embeddings for text using OpenAI's API.
    """
    # Model embedding yang direkomendasikan OpenAI saat ini.
    # Menghasilkan vektor dengan 1536 dimensi.
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536

    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not found in settings.")
        self.client = OpenAI(api_key=settings.openai_api_key.get_secret_value())
        print(f"✅ EmbeddingGenerator initialized with model: {self.EMBEDDING_MODEL}")

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
            
            # Panggil API Embeddings
            response = self.client.embeddings.create(
                input=[text_to_embed], 
                model=self.EMBEDDING_MODEL
            )
            
            # Ekstrak embedding dari respons
            embedding_vector = response.data[0].embedding
            
            # Verifikasi dimensi untuk keamanan
            if len(embedding_vector) != self.EMBEDDING_DIMENSIONS:
                print(f"⚠️ Warning: Embedding dimension mismatch. Expected {self.EMBEDDING_DIMENSIONS}, got {len(embedding_vector)}.")
                return None
            
            return embedding_vector

        except Exception as e:
            print(f"❌ An error occurred during embedding generation: {e}")
            return None