# prometheus/config/settings.py

from pydantic import SecretStr, PostgresDsn, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Manages all application settings using Pydantic V2.
    This is the definitive, type-safe, and runtime-correct version.
    """

    # --- Konfigurasi ---
    # Ini adalah cara paling robust di Pydantic V2 untuk mendefinisikan konfigurasi.
    # Kita membuat kamus konfigurasi dan langsung menetapkannya.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Opsi tambahan jika diperlukan, mis: extra='ignore'
    )

    # --- PostgreSQL (Odoo Database) Connection Settings ---
    postgres_user: str = Field(...)
    postgres_password: SecretStr = Field(...)
    postgres_host: str = Field(...)
    postgres_port: int = Field(...)
    postgres_db: str = Field(...)

    # --- Neo4j (Knowledge Graph) Connection Settings ---
    neo4j_user: str = Field(...)
    neo4j_password: SecretStr = Field(...)
    neo4j_uri: str = Field(...)

    # --- OpenAI API Settings ---
    openai_api_key: SecretStr = Field(...)

    # --- BARU: LLM Cost Models ---
    synthesis_model_name: str = Field(...)
    synthesis_price_input_usd_per_mtkn: float = Field(...)
    synthesis_price_output_usd_per_mtkn: float = Field(...)
    relation_model_name: str = Field(...)
    relation_price_input_usd_per_mtkn: float = Field(...)
    relation_price_output_usd_per_mtkn: float = Field(...)

    @property
    def pg_dsn(self) -> str:
        """Constructs the PostgreSQL DSN (Data Source Name) securely."""
        return str(PostgresDsn.build(
            scheme="postgresql+psycopg2",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            path=self.postgres_db,
        ))

# --- Singleton Instance ---
settings = Settings() #type: ignore