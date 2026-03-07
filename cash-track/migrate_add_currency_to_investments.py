"""Add currency column to investments table in Railway"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL not found in environment variables")
    print("Please set DATABASE_URL in your .env file or Railway environment")
    exit(1)

try:
    print("🔄 Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    print("🔄 Adding currency column to investments table...")
    cursor.execute("""
        ALTER TABLE investments
        ADD COLUMN IF NOT EXISTS currency VARCHAR(3) DEFAULT 'ARS'
    """)
    conn.commit()
    print("✅ Currency column added successfully")

    # Verify column was added
    print("🔄 Verifying column...")
    cursor.execute("""
        SELECT column_name, data_type, column_default
        FROM information_schema.columns
        WHERE table_name = 'investments' AND column_name = 'currency'
    """)
    result = cursor.fetchone()

    if result:
        print(f"✅ Verified: currency column exists")
        print(f"   - Column name: {result[0]}")
        print(f"   - Data type: {result[1]}")
        print(f"   - Default: {result[2]}")
    else:
        print("❌ Error: currency column was not added")

    # Show current investments count
    cursor.execute("SELECT COUNT(*) FROM investments")
    count = cursor.fetchone()[0]
    print(f"\n📊 Total investments in database: {count}")

    if count > 0:
        print("ℹ️  All existing investments will have currency='ARS' by default")

    cursor.close()
    conn.close()

    print("\n✅ Migration completed successfully!")

except Exception as e:
    print(f"❌ Error during migration: {e}")
    if 'conn' in locals():
        conn.rollback()
        conn.close()
    exit(1)
