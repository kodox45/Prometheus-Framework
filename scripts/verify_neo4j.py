# scripts/verify_neo4j.py

from prometheus.config.settings import settings
from prometheus.connectors.neo4j_connector import Neo4jConnector
from neo4j.exceptions import Neo4jError

def main():
    print("--- Verifying Neo4j Connector ---")

    try:
        # Use a 'with' block for the connector itself to manage the driver lifecycle
        with Neo4jConnector(settings) as neo4j_connector:
            print("Driver created. Attempting to get a session and run a query...")

            # Use a 'with' block for the session to manage the transaction
            with neo4j_connector.get_session() as session:
                # Run a simple query to confirm we can communicate with the DB
                result = session.run("RETURN 'Hello, Prometheus!' AS greeting")
                record = result.single()

                if record:
                    print(f"✅ Query successful! Neo4j says: '{record['greeting']}'")
                else:
                    print("🔥 Query ran but returned no result.")
    
    except Neo4jError as e:
        print(f"🔥 Database Error: Failed to connect or run query.")
        print(f"   Code: {e.code}")
        print(f"   Details: {e}")
        print("   Troubleshooting: Is Neo4j running? Are .env settings correct?")
    except Exception as e:
        print(f"🔥 An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()