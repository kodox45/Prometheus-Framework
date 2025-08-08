# prometheus/connectors/postgres_connector.py

from sqlalchemy import create_engine, inspect, Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine.reflection import Inspector

from prometheus.config.settings import Settings

class PostgresConnector:
    """
    Manages the connection and interactions with a PostgreSQL database
    using SQLAlchemy.
    """
    def __init__(self, settings: Settings):
        """
        Initializes the connector with database connection settings.

        Args:
            settings: The application settings object containing DB credentials.
        """
        self.dsn: str = settings.pg_dsn
        self.engine: Engine | None = None

    def connect(self) -> None:
        """
        Creates a SQLAlchemy engine. The engine manages a pool of connections
        and is the primary entry point for database operations.
        """
        if self.engine is not None:
            # Engine already created, do nothing.
            return
        
        try:
            # echo=False prevents SQLAlchemy from logging all generated SQL.
            # Set to True for deep debugging.
            self.engine = create_engine(self.dsn, echo=False)
            print("✅ SQLAlchemy Engine created for PostgreSQL.")
        except Exception as e:
            # Catch potential errors in DSN format or initial setup.
            print(f"❌ Could not create SQLAlchemy engine: {e}")
            raise

    def disconnect(self) -> None:
        """
        Disposes of the engine's connection pool.
        This is important for gracefully shutting down the application.
        """
        if self.engine:
            self.engine.dispose()
            self.engine = None
            print("🔌 SQLAlchemy Engine for PostgreSQL disposed.")

    def get_inspector(self) -> Inspector:
        """
        Provides a SQLAlchemy Inspector object for schema reflection.

        The Inspector is the key to reading database metadata like table names,
        column names, data types, and foreign keys.

        Returns:
            An Inspector instance for the current engine.
            
        Raises:
            ConnectionError: If the engine is not connected.
        """
        if not self.engine:
            raise ConnectionError("Not connected. Please call connect() before using the inspector.")
        
        return inspect(self.engine)

    # --- Context Management Support ---
    # These methods allow the class to be used with a 'with' statement.
    # e.g., with PostgresConnector(settings) as pg:
    #           # do stuff
    def __enter__(self):
        """Called when entering a 'with' block."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Called when exiting a 'with' block, ensuring disconnection."""
        self.disconnect()