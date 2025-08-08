# scripts/test_extractor.py

from prometheus.config.settings import settings
from prometheus.connectors.postgres_connector import PostgresConnector
from prometheus.genesis_engine.extractor import SchemaExtractor

def main():
    print("--- Testing Schema Extractor ---")
    
    # Gunakan 'with' untuk manajemen koneksi yang aman
    with PostgresConnector(settings) as pg_connector:
        extractor = SchemaExtractor(pg_connector)
        
        # Ekstrak skema 'public'
        database_schema = extractor.extract_schema(schema_name="public")
        
        # Verifikasi output
        num_tables = len(database_schema.tables)
        print(f"\n--- Extraction Summary ---")
        print(f"Total tables extracted: {num_tables}")
        
        if num_tables > 0:
            # Ambil contoh satu tabel, misalnya 'res_users' jika ada
            sample_table = next((t for t in database_schema.tables if t.table_name == 'res_users'), None)
            
            if sample_table:
                print("\n--- Sample Table: res_users ---")
                # Pydantic menyediakan metode .json() yang bagus untuk serialisasi
                # indent=2 membuat output JSON mudah dibaca
                print(sample_table.model_dump_json(indent=2))
            else:
                # Jika 'res_users' tidak ada, cetak saja tabel pertama
                print("\n--- Sample Table (First Found) ---")
                print(database_schema.tables[0].json(indent=2))

if __name__ == "__main__":
    main()