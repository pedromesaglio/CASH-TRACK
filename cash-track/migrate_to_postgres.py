#!/usr/bin/env python3
"""
Script de migración de SQLite a PostgreSQL
Este script copia todos los datos de cashtrack.db a PostgreSQL sin perder información

Uso:
  python3 migrate_to_postgres.py
"""

import sqlite3
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

# Configuración
SQLITE_DB = 'cashtrack.db'
POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'database': os.getenv('POSTGRES_DB', 'cashtrack'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', '')
}

def migrate_data():
    """Migrate all data from SQLite to PostgreSQL"""
    print("=== Migraci\u00f3n de SQLite a PostgreSQL ===\n")

    # Conectar a SQLite
    print(f"1. Conectando a SQLite ({SQLITE_DB})...")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    # Conectar a PostgreSQL
    print(f"2. Conectando a PostgreSQL ({POSTGRES_CONFIG['database']})...")
    try:
        pg_conn = psycopg2.connect(**POSTGRES_CONFIG)
        pg_cursor = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    except psycopg2.Error as e:
        print(f"\u274c Error conectando a PostgreSQL: {e}")
        print("\nPor favor ejecuta primero en tu terminal:")
        print("  sudo -u postgres createdb cashtrack")
        sqlite_conn.close()
        return False

    # Inicializar tablas en PostgreSQL
    print("3. Inicializando tablas en PostgreSQL...")
    os.environ['DB_TYPE'] = 'postgresql'
    from database import init_db
    try:
        init_db()
    except Exception as e:
        print(f"Error inicializando BD: {e}")

    # Reconectar después de init_db
    pg_conn = psycopg2.connect(**POSTGRES_CONFIG)
    pg_cursor = pg_conn.cursor()

    # Tabla de mapeo de IDs (importante para mantener relaciones)
    user_id_map = {}

    try:
        # 1. Migrar USERS
        print("\n4. Migrando usuarios...")
        sqlite_cursor.execute("SELECT * FROM users")
        users = sqlite_cursor.fetchall()

        for user in users:
            # Verificar si el usuario ya existe en PostgreSQL
            pg_cursor.execute(
                "SELECT id FROM users WHERE username = %s",
                (user['username'],)
            )
            existing = pg_cursor.fetchone()

            if existing:
                user_id_map[user['id']] = existing[0]
                print(f"   \u2139\ufe0f  Usuario '{user['username']}' ya existe, usando ID existente")
            else:
                pg_cursor.execute(
                    """INSERT INTO users (username, password, role, created_at)
                       VALUES (%s, %s, %s, %s) RETURNING id""",
                    (user['username'], user['password'], user['role'], user['created_at'])
                )
                new_id = pg_cursor.fetchone()[0]
                user_id_map[user['id']] = new_id
                print(f"   \u2705 Usuario '{user['username']}' migrado (ID: {user['id']} \u2192 {new_id})")

        pg_conn.commit()
        print(f"   \u2705 {len(users)} usuarios procesados")

        # 2. Migrar EXPENSES
        print("\n5. Migrando gastos...")
        sqlite_cursor.execute("SELECT * FROM expenses")
        expenses = sqlite_cursor.fetchall()

        for expense in expenses:
            new_user_id = user_id_map.get(expense['user_id'])
            if new_user_id:
                # Handle optional fields safely for sqlite3.Row
                currency = expense['currency'] if 'currency' in expense.keys() else 'ARS'
                installment = expense['installment_number'] if 'installment_number' in expense.keys() else None

                pg_cursor.execute(
                    """INSERT INTO expenses
                       (user_id, date, category, description, payment_method, amount, currency, installment_number, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (new_user_id, expense['date'], expense['category'], expense['description'],
                     expense['payment_method'], expense['amount'],
                     currency, installment,
                     expense['created_at'])
                )

        pg_conn.commit()
        print(f"   \u2705 {len(expenses)} gastos migrados")

        # 3. Migrar INCOME
        print("\n6. Migrando ingresos...")
        sqlite_cursor.execute("SELECT * FROM income")
        incomes = sqlite_cursor.fetchall()

        for income in incomes:
            new_user_id = user_id_map.get(income['user_id'])
            if new_user_id:
                pg_cursor.execute(
                    """INSERT INTO income (user_id, date, source, amount, created_at)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (new_user_id, income['date'], income['source'], income['amount'], income['created_at'])
                )

        pg_conn.commit()
        print(f"   \u2705 {len(incomes)} ingresos migrados")

        # 4. Migrar INVESTMENTS
        print("\n7. Migrando inversiones...")
        sqlite_cursor.execute("SELECT * FROM investments")
        investments = sqlite_cursor.fetchall()

        for inv in investments:
            new_user_id = user_id_map.get(inv['user_id'])
            if new_user_id:
                # Handle optional symbol field
                symbol = inv['symbol'] if 'symbol' in inv.keys() else None

                pg_cursor.execute(
                    """INSERT INTO investments
                       (user_id, date, type, name, amount, current_value, notes, symbol, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (new_user_id, inv['date'], inv['type'], inv['name'], inv['amount'],
                     inv['current_value'], inv['notes'], symbol, inv['created_at'])
                )

        pg_conn.commit()
        print(f"   \u2705 {len(investments)} inversiones migradas")

        # 5. Migrar CUSTOM CATEGORIES
        print("\n8. Migrando categor\u00edas personalizadas...")
        sqlite_cursor.execute("SELECT * FROM custom_categories")
        categories = sqlite_cursor.fetchall()

        for cat in categories:
            new_user_id = user_id_map.get(cat['user_id'])
            if new_user_id:
                try:
                    pg_cursor.execute(
                        """INSERT INTO custom_categories (user_id, name, icon, created_at)
                           VALUES (%s, %s, %s, %s)""",
                        (new_user_id, cat['name'], cat['icon'], cat['created_at'])
                    )
                except psycopg2.IntegrityError:
                    # Categor\u00eda ya existe, omitir
                    pg_conn.rollback()
                    continue
                pg_conn.commit()

        print(f"   \u2705 {len(categories)} categor\u00edas migradas")

        # 6. Migrar BINANCE CREDENTIALS
        print("\n9. Migrando credenciales de Binance...")
        sqlite_cursor.execute("SELECT * FROM binance_credentials")
        credentials = sqlite_cursor.fetchall()

        for cred in credentials:
            new_user_id = user_id_map.get(cred['user_id'])
            if new_user_id:
                try:
                    pg_cursor.execute(
                        """INSERT INTO binance_credentials
                           (user_id, api_key, api_secret, is_testnet, created_at, updated_at)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (new_user_id, cred['api_key'], cred['api_secret'],
                         bool(cred['is_testnet']), cred['created_at'], cred['updated_at'])
                    )
                except psycopg2.IntegrityError:
                    # Credencial ya existe, actualizar
                    pg_conn.rollback()
                    pg_cursor.execute(
                        """UPDATE binance_credentials
                           SET api_key = %s, api_secret = %s, is_testnet = %s, updated_at = %s
                           WHERE user_id = %s""",
                        (cred['api_key'], cred['api_secret'], bool(cred['is_testnet']),
                         cred['updated_at'], new_user_id)
                    )
                pg_conn.commit()

        print(f"   \u2705 {len(credentials)} credenciales migradas")

        # Verificaci\u00f3n final
        print("\n10. Verificando migraci\u00f3n...")
        pg_cursor.execute("SELECT COUNT(*) FROM users")
        pg_users = pg_cursor.fetchone()[0]

        pg_cursor.execute("SELECT COUNT(*) FROM expenses")
        pg_expenses = pg_cursor.fetchone()[0]

        pg_cursor.execute("SELECT COUNT(*) FROM income")
        pg_income = pg_cursor.fetchone()[0]

        pg_cursor.execute("SELECT COUNT(*) FROM investments")
        pg_investments = pg_cursor.fetchone()[0]

        print(f"\nResumen de la migraci\u00f3n:")
        print(f"  Usuarios: {len(users)} (SQLite) \u2192 {pg_users} (PostgreSQL)")
        print(f"  Gastos: {len(expenses)} (SQLite) \u2192 {pg_expenses} (PostgreSQL)")
        print(f"  Ingresos: {len(incomes)} (SQLite) \u2192 {pg_income} (PostgreSQL)")
        print(f"  Inversiones: {len(investments)} (SQLite) \u2192 {pg_investments} (PostgreSQL)")

        print("\n\u2705 \u00a1Migraci\u00f3n completada exitosamente!")
        print("\nPr\u00f3ximos pasos:")
        print("1. Verifica que los datos est\u00e9n correctos en PostgreSQL")
        print("2. El archivo .env ya est\u00e1 configurado para usar PostgreSQL")
        print("3. Reinicia el servidor: python app.py")
        print("4. El backup de SQLite est\u00e1 en cashtrack_backup_*.db por seguridad")

        return True

    except Exception as e:
        print(f"\n\u274c Error durante la migraci\u00f3n: {e}")
        import traceback
        traceback.print_exc()
        pg_conn.rollback()
        return False

    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == "__main__":
    success = migrate_data()
    if success:
        print("\n\u2728 \u00a1Todo listo! Tu base de datos ahora usa PostgreSQL.")
    else:
        print("\n\u26a0\ufe0f  La migraci\u00f3n no se complet\u00f3. Revisa los errores arriba.")
