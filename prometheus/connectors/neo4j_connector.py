# prometheus/connectors/neo4j_connector.py

from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import Neo4jError

from prometheus.config.settings import Settings

class Neo4jConnector:
    """
    Manages the connection and interactions with a Neo4j graph database.
    """
    def __init__(self, settings: Settings):
        """
        Initializes the connector with Neo4j connection settings.

        Args:
            settings: The application settings object containing Neo4j credentials.
        """
        self.uri: str = settings.neo4j_uri
        # The official driver expects a tuple for authentication.
        self.auth: tuple[str, str] = (settings.neo4j_user, settings.neo4j_password.get_secret_value())
        self.driver: Driver | None = None

    def connect(self) -> None:
        """
        Creates and verifies a connection to the Neo4j database.
        """
        if self.driver:
            return

        try:
            self.driver = GraphDatabase.driver(self.uri, auth=self.auth)
            # verify_connectivity() pings the server to ensure it's reachable.
            self.driver.verify_connectivity()
            print("✅ Neo4j Driver created and connection verified.")
        except Exception as e:
            print(f"❌ Could not connect to Neo4j: {e}")
            raise

    def disconnect(self) -> None:
        """
        Closes the driver and all its connections.
        """
        if self.driver:
            self.driver.close()
            self.driver = None
            print("🔌 Neo4j Driver closed.")

    def get_session(self) -> Session:
        """
        Provides a Neo4j Session for executing queries.
        
        The caller is responsible for closing the session, ideally using a
        'with' statement.
        
        Returns:
            A new Session object from the driver.

        Raises:
            ConnectionError: If the driver is not connected.
        """
        if not self.driver:
            raise ConnectionError("Not connected. Please call connect() before getting a session.")
        return self.driver.session()

    # --- Context Management Support ---
    def __enter__(self):
        """Called when entering a 'with' block."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Called when exiting a 'with' block, ensuring disconnection."""
        self.disconnect()