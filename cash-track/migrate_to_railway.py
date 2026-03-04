"""
Script to migrate data from local PostgreSQL to Railway PostgreSQL
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Local database config
LOCAL_DB = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'database': os.getenv('POSTGRES_DB', 'cashtrack'),
    'user': os.getenv('POSTGRES_USER', 'pedro'),
    'password': os.getenv('POSTGRES_PASSWORD', '')
}

# Railway database URL (you'll need to provide this)
RAILWAY_DATABASE_URL = input("Enter Railway DATABASE_URL: ")

def export_data():
    """Export all data from local database"""
    print("Connecting to local database...")
    local_conn = psycopg2.connect(**LOCAL_DB)
    local_cursor = local_conn.cursor()

    data = {}

    # Export users
    print("Exporting users...")
    local_cursor.execute("SELECT id, username, password, role, created_at FROM users")
    data['users'] = local_cursor.fetchall()

    # Export expenses (map local schema to Railway schema)
    print("Exporting expenses...")
    # Local: id, user_id, date, category, description, payment_method, amount, currency, installment_number, created_at
    # Railway: id, user_id, amount, category, description, date, created_at, receipt_filename, payment_method, subcategory, notes
    local_cursor.execute("""
        SELECT id, user_id, amount, category, description, date, created_at,
               NULL as receipt_filename, payment_method, NULL as subcategory, NULL as notes
        FROM expenses
    """)
    data['expenses'] = local_cursor.fetchall()

    # Export income
    print("Exporting income...")
    # Local: id, user_id, date, source, amount, created_at
    # Railway: id, user_id, amount, source, date, created_at
    local_cursor.execute("""
        SELECT id, user_id, amount, source, date, created_at
        FROM income
    """)
    data['income'] = local_cursor.fetchall()

    # Export investments
    print("Exporting investments...")
    # Local: id, user_id, date, type, name, amount, current_value, notes, symbol, created_at
    # Railway: id, user_id, name, type, amount, current_value, purchase_date, created_at, notes, quantity
    local_cursor.execute("""
        SELECT id, user_id, name, type, amount, current_value, date as purchase_date, created_at, notes, NULL as quantity
        FROM investments
    """)
    data['investments'] = local_cursor.fetchall()

    # Export custom categories
    print("Exporting custom categories...")
    # Local: id, user_id, name, icon, created_at
    # Railway: id, user_id, category_name, category_type, created_at
    # Note: Local doesn't have category_type, defaulting to 'expense'
    local_cursor.execute("""
        SELECT id, user_id, name as category_name, 'expense' as category_type, created_at
        FROM custom_categories
    """)
    data['custom_categories'] = local_cursor.fetchall()

    # Export binance credentials
    print("Exporting binance credentials...")
    # Local: id, user_id, api_key, api_secret, is_testnet, created_at, updated_at
    # Railway: id, user_id, api_key, api_secret, created_at, is_testnet, last_synced
    local_cursor.execute("""
        SELECT id, user_id, api_key, api_secret, created_at, is_testnet, NULL as last_synced
        FROM binance_credentials
    """)
    data['binance_credentials'] = local_cursor.fetchall()

    local_conn.close()
    return data

def import_data(data):
    """Import all data to Railway database"""
    print("Connecting to Railway database...")
    railway_conn = psycopg2.connect(RAILWAY_DATABASE_URL)
    railway_cursor = railway_conn.cursor()

    # Import users
    print(f"Importing {len(data['users'])} users...")
    for user in data['users']:
        railway_cursor.execute(
            "INSERT INTO users (id, username, password, role, created_at) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (username) DO NOTHING",
            user
        )

    # Import expenses
    print(f"Importing {len(data['expenses'])} expenses...")
    for expense in data['expenses']:
        railway_cursor.execute(
            """INSERT INTO expenses
               (id, user_id, amount, category, description, date, created_at, receipt_filename, payment_method, subcategory, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (id) DO NOTHING""",
            expense
        )

    # Import income
    print(f"Importing {len(data['income'])} income records...")
    for inc in data['income']:
        railway_cursor.execute(
            """INSERT INTO income
               (id, user_id, amount, source, date, created_at)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (id) DO NOTHING""",
            inc
        )

    # Import investments
    print(f"Importing {len(data['investments'])} investments...")
    for inv in data['investments']:
        railway_cursor.execute(
            """INSERT INTO investments
               (id, user_id, name, type, amount, current_value, purchase_date, created_at, notes, quantity)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (id) DO NOTHING""",
            inv
        )

    # Import custom categories
    print(f"Importing {len(data['custom_categories'])} custom categories...")
    for cat in data['custom_categories']:
        railway_cursor.execute(
            """INSERT INTO custom_categories
               (id, user_id, category_name, category_type, created_at)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (user_id, category_name, category_type) DO NOTHING""",
            cat
        )

    # Import binance credentials
    print(f"Importing {len(data['binance_credentials'])} binance credentials...")
    for cred in data['binance_credentials']:
        railway_cursor.execute(
            """INSERT INTO binance_credentials
               (id, user_id, api_key, api_secret, created_at, is_testnet, last_synced)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (user_id) DO NOTHING""",
            cred
        )

    railway_conn.commit()
    railway_conn.close()
    print("✅ Migration completed successfully!")

if __name__ == '__main__':
    try:
        data = export_data()
        import_data(data)
    except Exception as e:
        print(f"❌ Error: {e}")
