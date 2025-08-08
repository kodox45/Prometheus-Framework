# scripts/run_seeder.py

import random
from typing import Dict, List, Any
from graphlib import TopologicalSorter, CycleError

from prometheus.config.settings import settings
from prometheus.connectors.neo4j_connector import Neo4jConnector
from prometheus.connectors.postgres_connector import PostgresConnector
from prometheus.seeder.kg_interrogator import KGInterrogator
from prometheus.seeder.data_generator import DataGenerator
from prometheus.seeder.data_injector import DataInjector

def get_table_info(interrogator: KGInterrogator, table_name: str) -> Dict:
    """Helper untuk mendapatkan info kolom berdasarkan nama tabel."""
    columns = interrogator.get_table_columns(table_name)
    if not columns:
        raise RuntimeError(f"Could not get column info for {table_name}")
    return {"name": table_name, "columns": columns}

def main(num_customers: int = 10, num_products: int = 20, num_orders: int = 50):
    """
    Menjalankan alur kerja Genesis Seeder secara end-to-end, menangani
    dependensi yang kompleks dan dependensi melingkar.
    """
    print("--- Running Final Genesis Seeder ---")
    
    with Neo4jConnector(settings) as neo4j_connector, \
         PostgresConnector(settings) as pg_connector:
        
        # 1. Inisialisasi semua komponen
        interrogator = KGInterrogator(neo4j_connector)
        data_gen = DataGenerator()
        injector = DataInjector(pg_connector)
        
        generated_ids: Dict[str, List[int]] = {}

        # ======================================================================
        # FASE 1: Menemukan Entitas & Membangun Graf Dependensi
        # ======================================================================
        print("\n[Phase 1/4] Discovering entities and building dependency graph...")
        
        try:
            customer_table_name = interrogator.find_table_by_keywords(['partner'])
            product_table_name = interrogator.find_table_by_keywords(['product'], ['tag', 'category', 'template'])
            order_table_name = interrogator.find_table_by_keywords(['sale', 'order'], ['line', 'item'])
        except RuntimeError as e:
            print(f"❌ Initial entity discovery failed: {e}")
            return

        # Kumpulkan semua tabel yang perlu kita buat datanya
        all_required_tables = {customer_table_name, product_table_name, order_table_name}
        initial_deps = interrogator.get_table_dependencies(order_table_name)
        all_required_tables.update(initial_deps)

        # Bangun graf dependensi menggunakan TopologicalSorter
        ts = TopologicalSorter()
        table_metadata = {}
        
        # Daftar ini adalah hasil dari debugging kita untuk memutus siklus di skema Odoo
        ignore_dependencies = {
            ('res_company', 'res_partner'),
            ('account_journal', 'res_company'),
            ('sale_order_template', 'res_company'),
            ('res_users', 'res_company'),
            ('res_partner', 'res_users'),
            ('res_currency', 'res_users'),
            ('mail_template', 'res_users'),
            ('res_users', 'product_product'),
            ('crm_team', 'res_users'),
            ('res_users', 'res_partner'),
            ('res_users', 'account_journal'),
            ('res_company', 'crm_team'),
            ('res_users', 'crm_team'),
        }
        
        for table_name in sorted(list(all_required_tables)): # Urutkan untuk konsistensi
            if not table_name: continue
            
            table_metadata[table_name] = get_table_info(interrogator, table_name)
            dependencies = interrogator.get_table_dependencies(table_name)
            filtered_deps = [dep for dep in dependencies if (table_name, dep) not in ignore_dependencies]
            ts.add(table_name, *filtered_deps)
        
        try:
            seeding_order = list(ts.static_order())
            print(f"  ✅ Determined seeding order for {len(seeding_order)} tables.")
        except CycleError as e:
            print(f"❌ A cycle was detected that was not handled: {e}")
            print("   > Consider adding one of the cycle's edges to the 'ignore_dependencies' list.")
            return

        # ======================================================================
        # FASE 2: Seeding Data Dependensi dan Master
        # ======================================================================
        print("\n[Phase 2/4] Seeding dependency and master data in order...")
        for table_name in seeding_order:
            if table_name not in table_metadata: continue

            table_info = table_metadata[table_name]
            is_core_table = table_name in [customer_table_name, product_table_name]
            
            if is_core_table:
                num_records = num_customers if table_name == customer_table_name else num_products
            else:
                num_records = 1

            print(f"  - Seeding {num_records} record(s) for '{table_name}'...")
            generated_ids.setdefault(table_name, [])
            
            dependencies = interrogator.get_table_dependencies(table_name)
            
            for _ in range(num_records):
                fk_values = {}
                for dep_table_name in dependencies:
                    if dep_table_name in generated_ids and generated_ids[dep_table_name]:
                        base_dep_name = dep_table_name.split('.')[-1].replace('res_', '').replace('product_', '').replace('account_', '')
                        possible_fk_cols = [c for c in table_info['columns'] if base_dep_name in c['name'] and c['name'].endswith('_id')]
                        for col_info in possible_fk_cols:
                            fk_values[col_info['name']] = random.choice(generated_ids[dep_table_name])

                if is_core_table:
                    record_data = data_gen.generate_record_data(table_name, table_info['columns'], foreign_keys=fk_values)
                else:
                    record_data = data_gen.generate_minimal_dummy_record(table_name, table_info['columns'], foreign_keys=fk_values)
                
                new_id = injector.insert_record(table_name, record_data)
                if new_id:
                    generated_ids[table_name].append(new_id)

        print("  ✅ Dependency and master data seeded.")
        
        # ======================================================================
        # FASE 3: Seeding Data Transaksional (Sales Orders)
        # ======================================================================
        print(f"\n[Phase 3/4] Seeding {num_orders} transactional data (Sales Orders)...")
        order_info = table_metadata[order_table_name]
        order_ids = []
        dependencies = interrogator.get_table_dependencies(order_table_name)
        for i in range(num_orders):
            fk_values = {}
            for dep_table_name in dependencies:
                if dep_table_name in generated_ids and generated_ids[dep_table_name]:
                    base_dep_name = dep_table_name.split('.')[-1].replace('res_', '').replace('product_', '').replace('account_', '')
                    possible_fk_cols = [c for c in order_info['columns'] if base_dep_name in c['name'] and c['name'].endswith('_id')]
                    for col_info in possible_fk_cols:
                        fk_values[col_info['name']] = random.choice(generated_ids[dep_table_name])
            
            order_data = data_gen.generate_record_data(order_table_name, order_info['columns'], foreign_keys=fk_values)
            new_id = injector.insert_record(order_table_name, order_data)
            if new_id:
                order_ids.append(new_id)
        
        print(f"  ✅ {len(order_ids)} sales orders injected successfully.")

        # ======================================================================
        # FASE 4: Ringkasan Final
        # ======================================================================
        print("\n[Phase 4/4] Final summary.")
        for table_name in seeding_order:
             if table_name in generated_ids:
                 print(f"  - Generated {len(generated_ids[table_name])} IDs for '{table_name}'")
        
    print("\n🎉 --- Final Genesis Seeder finished successfully! --- 🎉")

if __name__ == "__main__":
    # Jalankan seeder dengan jumlah data yang diinginkan
    main(num_customers=10, num_products=20, num_orders=50)