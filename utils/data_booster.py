# utils/data_booster.py

import xmlrpc.client
import random
from faker import Faker
from datetime import datetime

# --- 1. KONFIGURASI ---
ODOO_URL = "http://localhost:8069"
ODOO_DB = "salescrm"
ODOO_USER = "farezayuza@gmail.com"
ODOO_PASSWORD = "salescrm"
NUM_NEW_SALE_ORDERS = 2000 # Mari kita buat lebih sedikit untuk pengujian awal
MAX_ORDER_LINES_PER_ORDER = 5

# Inisialisasi Faker
fake = Faker()

class OdooApiBooster:
    def __init__(self, url, db, user, password):
        self.url = url
        self.db = db
        self.user = user
        self.password = password
        self.uid = None
        self.models = None
        print("Initializing Odoo API Booster...")

    def connect(self):
        """Menghubungkan ke Odoo dan mengotentikasi user."""
        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            version = common.version()
            print(f"Connected to Odoo version: {version['server_version']}")
            self.uid = common.authenticate(self.db, self.user, self.password, {})
            if not self.uid: raise Exception("Authentication failed.")
            print(f"Authentication successful. User ID: {self.uid}")
            self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            raise

    def fetch_master_data(self):
        """Mengambil ID dari data master yang ada (Pelanggan & Produk)."""
        print("\nFetching master data IDs for booster...")
        try:
            # Cari semua pelanggan (partner) yang merupakan 'company'
            customer_ids = self.models.execute_kw(self.db, self.uid, self.password,
                'res.partner', 'search', [[['is_company', '=', True]]])
            
            # Cari semua produk yang bisa dijual dan memiliki harga jual
            product_data = self.models.execute_kw(self.db, self.uid, self.password,
                'product.product', 'search_read',
                [[['sale_ok', '=', True], ['list_price', '>', 0]]],
                {'fields': ['id', 'list_price']})

            if not customer_ids or not product_data:
                raise Exception("Master data (customers/products) not found. Ensure demo data is loaded.")
                
            print(f"Found {len(customer_ids)} customers and {len(product_data)} sellable products.")
            return customer_ids, product_data
        except Exception as e:
            print(f"❌ Failed to fetch master data: {e}")
            raise

    def create_sale_orders(self, customer_ids, product_data, num_orders):
        """Membuat sejumlah pesanan penjualan baru yang valid secara logis."""
        print(f"\nStarting generation of {num_orders} new sale orders...")
        created_count = 0
        for i in range(num_orders):
            try:
                # --- A. Pilih Data Acak dari Master Data yang Ada ---
                customer_id = random.choice(customer_ids)
                num_lines = random.randint(1, MAX_ORDER_LINES_PER_ORDER)
                
                # --- B. Buat Item Baris (Order Lines) ---
                order_lines = []
                # Ambil sampel produk unik untuk pesanan ini
                products_for_order = random.sample(product_data, min(num_lines, len(product_data)))

                for product in products_for_order:
                    quantity = random.randint(1, 20)
                    # (0, 0, {values}) berarti 'create record'
                    order_lines.append((0, 0, {
                        'product_id': product['id'],
                        'product_uom_qty': quantity,
                        'price_unit': product['list_price'], # Gunakan harga dari produk
                    }))
                
                # --- C. Buat Dictionary Nilai untuk Sale Order ---
                # Hanya sediakan field yang kita tahu WAJIB dan TIDAK READONLY
                order_values = {
                    'partner_id': customer_id,
                    'date_order': fake.past_datetime(start_date="-1y").strftime('%Y-%m-%d %H:%M:%S'),
                    'order_line': order_lines,
                }
                
                # --- D. Panggil 'create' dan 'action_confirm' ---
                order_id = self.models.execute_kw(self.db, self.uid, self.password,
                    'sale.order', 'create', [order_values])
                
                self.models.execute_kw(self.db, self.uid, self.password,
                    'sale.order', 'action_confirm', [[order_id]])

                created_count += 1
                print(f"  ({i+1}/{num_orders}) -> Created and confirmed Sale Order ID: {order_id}")

            except xmlrpc.client.Fault as e:
                print(f"  - Odoo Error on order {i+1}: {e.faultString}")
            except Exception as e:
                print(f"  - General Error on order {i+1}: {e}")
        
        print(f"\n✅ Finished. Successfully created {created_count} sale orders.")

    def run(self):
        """Menjalankan seluruh alur kerja booster."""
        try:
            self.connect()
            customer_ids, product_data = self.fetch_master_data()
            self.create_sale_orders(customer_ids, product_data, NUM_NEW_SALE_ORDERS)
        except Exception as e:
            print(f"\n💥 An error stopped the booster: {e}")


# --- Entry Point ---
if __name__ == "__main__":
    booster = OdooApiBooster(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD)
    booster.run()