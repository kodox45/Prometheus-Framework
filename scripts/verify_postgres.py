# scripts/verify_postgres.py

from prometheus.config.settings import settings
from prometheus.connectors.postgres_connector import PostgresConnector
from sqlalchemy.exc import SQLAlchemyError

def main():
    print("--- Verifying PostgreSQL Connector ---")

    try:
        # Using the 'with' statement to ensure connection is managed properly.
        with PostgresConnector(settings) as pg_connector:
            print("Attempting to get an inspector...")
            inspector = pg_connector.get_inspector()
            
            print("Inspector acquired. Attempting to get schema names...")
            schemas = inspector.get_schema_names()
            
            print(f"✅ Connection successful! Found schemas: {schemas}")
            
            # A more specific test for Odoo: check for a common table.
            print("Attempting to get table names...")
            tables = inspector.get_table_names(schema='public')
            if 'res_users' in tables:
                print("✅ Found 'res_users' table. Odoo database confirmed!")
            else:
                print("⚠️ Could not find 'res_users' table. Is this the correct Odoo database?")

    except SQLAlchemyError as e:
        print(f"🔥 Database Error: Failed to connect or inspect the database.")
        print(f"   Details: {e}")
        print("   Troubleshooting: Is PostgreSQL running? Are .env settings correct?")
    except ConnectionError as e:
        print(f"🔥 Connection Management Error: {e}")
    except Exception as e:
        print(f"🔥 An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()