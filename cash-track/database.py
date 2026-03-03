import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

# Load environment variables
load_dotenv()

# Database configuration
DB_TYPE = os.getenv('DB_TYPE', 'sqlite')  # 'sqlite' or 'postgresql'

# SQLite configuration
SQLITE_DATABASE = 'cashtrack.db'

# PostgreSQL configuration
POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'database': os.getenv('POSTGRES_DB', 'cashtrack'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', '')
}

def get_db():
    """Get database connection based on DB_TYPE"""
    if DB_TYPE == 'postgresql':
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(
            host=POSTGRES_CONFIG['host'],
            port=POSTGRES_CONFIG['port'],
            database=POSTGRES_CONFIG['database'],
            user=POSTGRES_CONFIG['user'],
            password=POSTGRES_CONFIG['password']
        )
        # Use DictCursor to get results as dictionaries (similar to SQLite Row)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn
    else:
        # SQLite (default)
        import sqlite3
        conn = sqlite3.connect(SQLITE_DATABASE)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    """Initialize database with tables"""
    conn = get_db()
    cursor = conn.cursor()

    if DB_TYPE == 'postgresql':
        # PostgreSQL table creation
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Expenses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                payment_method TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'ARS',
                installment_number TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        # Income table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS income (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL,
                source TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        # Investments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS investments (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                current_value REAL,
                notes TEXT,
                symbol TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        # Custom categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_categories (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                icon TEXT DEFAULT '📦',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, name)
            )
        ''')

        # Binance API credentials table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS binance_credentials (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE,
                api_key TEXT NOT NULL,
                api_secret TEXT NOT NULL,
                is_testnet BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        # Create default admin user
        cursor.execute(
            "SELECT 1 FROM users WHERE username = %s",
            ('admin',)
        )
        if not cursor.fetchone():
            cursor.execute(
                'INSERT INTO users (username, password, role) VALUES (%s, %s, %s)',
                ('admin', generate_password_hash('admin'), 'admin')
            )

    else:
        # SQLite table creation (original code)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                payment_method TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS income (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL,
                source TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS investments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                current_value REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                icon TEXT DEFAULT '📦',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, name)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS binance_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                api_key TEXT NOT NULL,
                api_secret TEXT NOT NULL,
                is_testnet BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id)
            )
        ''')

        # Add columns if they don't exist (SQLite only)
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN role TEXT DEFAULT "user"')
        except:
            pass

        try:
            cursor.execute('ALTER TABLE investments ADD COLUMN symbol TEXT')
        except:
            pass

        try:
            cursor.execute('ALTER TABLE expenses ADD COLUMN installment_number TEXT')
        except:
            pass

        try:
            cursor.execute('ALTER TABLE expenses ADD COLUMN currency TEXT DEFAULT "ARS"')
        except:
            pass

        # Create default admin user (SQLite)
        try:
            cursor.execute(
                'INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                ('admin', generate_password_hash('admin'), 'admin')
            )
        except:
            # User already exists, update role to admin
            cursor.execute('UPDATE users SET role = ? WHERE username = ?', ('admin', 'admin'))

    conn.commit()
    conn.close()
    print(f'✅ Database initialized successfully using {DB_TYPE.upper()}!')

if __name__ == '__main__':
    init_db()
