# scripts/test_config.py
from prometheus.config.settings import settings

print("--- Testing Settings Module (Pydantic V2) ---")
try:
    print(f"Postgres User: {settings.postgres_user}")
    print(f"Postgres Password: {settings.postgres_password}")
    print(f"Postgres DSN: {settings.pg_dsn}")
    print(f"OpenAI Key is loaded: {settings.openai_api_key is not None}")
    print("\n✅ Settings module loaded successfully!")
except Exception as e:
    print(f"\n❌ Error loading settings module: {e}")
    print("--> Please ensure your .env file exists and is correctly filled out.")