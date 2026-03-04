"""
Script to initialize Railway database with all tables
"""
import psycopg2
import sys

# Railway database URL
RAILWAY_DATABASE_URL = "postgresql://postgres:eMcCzPWdkacleqMeFBnqNGYoNnQmvEwF@hopper.proxy.rlwy.net:22426/railway"

def init_railway_database():
    """Create all tables in Railway database"""
    print("Connecting to Railway database...")
    try:
        conn = psycopg2.connect(RAILWAY_DATABASE_URL)
        cursor = conn.cursor()

        # Create users table
        print("Creating users table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                password VARCHAR(200) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create expenses table
        print("Creating expenses table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category VARCHAR(50) NOT NULL,
                description TEXT,
                date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                receipt_filename VARCHAR(255),
                payment_method VARCHAR(50) DEFAULT 'cash',
                subcategory VARCHAR(50),
                notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Create income table
        print("Creating income table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS income (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                source VARCHAR(100) NOT NULL,
                date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Create investments table
        print("Creating investments table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS investments (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name VARCHAR(100) NOT NULL,
                type VARCHAR(50) NOT NULL,
                amount REAL NOT NULL,
                current_value REAL,
                purchase_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                quantity REAL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Create custom_categories table
        print("Creating custom_categories table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_categories (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                category_name VARCHAR(50) NOT NULL,
                category_type VARCHAR(20) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE (user_id, category_name, category_type)
            )
        ''')

        # Create binance_credentials table
        print("Creating binance_credentials table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS binance_credentials (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                api_key TEXT NOT NULL,
                api_secret TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_testnet BOOLEAN DEFAULT FALSE,
                last_synced TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE (user_id)
            )
        ''')

        conn.commit()
        print("✅ All tables created successfully!")

        # Verify tables
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        print(f"\n📋 Tables in database: {[table[0] for table in tables]}")

        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    init_railway_database()
