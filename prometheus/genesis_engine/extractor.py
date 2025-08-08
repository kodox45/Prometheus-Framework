# prometheus/genesis_engine/extractor.py

from sqlalchemy.engine.reflection import Inspector

from prometheus.connectors.postgres_connector import PostgresConnector
from prometheus.genesis_engine.models import DatabaseSchema, TableSchema, ColumnSchema, ForeignKeySchema

class SchemaExtractor:
    """
    Extracts the raw schema information from a database using a connector.
    """
    def __init__(self, connector: PostgresConnector):
        """
        Initializes the extractor with a database connector.

        Args:
            connector: An instance of PostgresConnector.
        """
        self.connector = connector

    def extract_schema(self, schema_name: str = "public") -> DatabaseSchema:
        """
        Extracts all tables, columns, and foreign keys from a given schema.

        Args:
            schema_name: The name of the database schema to inspect (e.g., 'public').

        Returns:
            A DatabaseSchema object containing the structured schema information.
        """
        print(f"🚀 Starting schema extraction from '{schema_name}'...")
        
        self.connector.connect()
        inspector = self.connector.get_inspector()

        db_schema = DatabaseSchema()
        table_names = inspector.get_table_names(schema=schema_name)
        print(f"Found {len(table_names)} tables. Inspecting each one...")

        for table_name in table_names:
            # 1. Ekstrak Kolom
            columns_data = inspector.get_columns(table_name, schema=schema_name)
            columns = [
                ColumnSchema(
                    name=col['name'],
                    data_type=str(col['type']), # Konversi tipe SQLAlchemy ke string
                    is_nullable=col['nullable'],
                    comment=col.get('comment')
                ) for col in columns_data
            ]

            # 2. Ekstrak Foreign Keys
            fks_data = inspector.get_foreign_keys(table_name, schema=schema_name)
            foreign_keys = [
                ForeignKeySchema(
                    constrained_columns=fk['constrained_columns'],
                    referred_schema=fk.get('referred_schema'), # type: ignore
                    referred_table=fk['referred_table'],
                    referred_columns=fk['referred_columns'],
                    on_update=fk.get('options', {}).get('onupdate', '').upper() or None,
                    on_delete=fk.get('options', {}).get('ondelete', '').upper() or None,
                ) for fk in fks_data
            ]
            
            # 3. Ekstrak Komentar Tabel (jika ada)
            table_comment = inspector.get_table_comment(table_name, schema=schema_name).get('text')

            # 4. Ekstrak Primary Key
            pk_constraint = inspector.get_pk_constraint(table_name, schema=schema_name)
            primary_key_cols = pk_constraint.get('constrained_columns', [])
            
            # 5. Ekstrak Unique Constraints
            unique_constraints = inspector.get_unique_constraints(table_name, schema=schema_name)
            
            # 6. Ekstrak Indexes
            indexes = inspector.get_indexes(table_name, schema=schema_name)

            # 7. Junction Table
            is_junction = False
            # Aturan: Tabel adalah junction jika >50% kolomnya adalah bagian dari FK
            # dan jumlah FK >= 2, dan tidak ada kolom non-FK (selain PK itu sendiri).
            # Ini adalah heuristik yang lebih kuat.
            if len(foreign_keys) >= 2 and primary_key_cols:
                # Kumpulkan semua kolom yang merupakan bagian dari suatu FK
                fk_column_names = {col for fk in foreign_keys for col in fk.constrained_columns}
                
                # Jika semua kolom PK adalah juga kolom FK
                if set(primary_key_cols).issubset(fk_column_names):
                    # Kumpulkan semua nama kolom non-PK
                    non_pk_columns = {c.name for c in columns if c.name not in primary_key_cols}
                    # Jika tidak ada kolom non-PK yang bukan juga bagian dari FK, maka ini junction table
                    if not non_pk_columns.difference(fk_column_names):
                        is_junction = True
                        print(f"  - Detected '{table_name}' as a Junction Table.")
                        
            # 8. Gabungkan menjadi objek TableSchema
            table_schema = TableSchema(
                schema_name=schema_name,
                table_name=table_name,
                columns=columns,
                foreign_keys=foreign_keys,
                comment=table_comment,
                primary_key=primary_key_cols,
                unique_constraints=unique_constraints, # type: ignore
                is_junction_table=is_junction,
                indexes=indexes # type: ignore
            )
            db_schema.tables.append(table_schema)
            print(f"  - Inspected table '{table_name}'")

        print("✅ Schema extraction completed successfully.")
        return db_schema