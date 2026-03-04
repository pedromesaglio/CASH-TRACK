"""Verify data migrated to Railway"""
import psycopg2

RAILWAY_DATABASE_URL = 'postgresql://postgres:eMcCzPWdkacleqMeFBnqNGYoNnQmvEwF@hopper.proxy.rlwy.net:22426/railway'

conn = psycopg2.connect(RAILWAY_DATABASE_URL)
cursor = conn.cursor()

print('=== RAILWAY DATABASE VERIFICATION ===\n')

# Count users
cursor.execute('SELECT COUNT(*) FROM users')
print(f'Users: {cursor.fetchone()[0]}')

# Count expenses
cursor.execute('SELECT COUNT(*) FROM expenses')
print(f'Expenses: {cursor.fetchone()[0]}')

# Count income
cursor.execute('SELECT COUNT(*) FROM income')
print(f'Income: {cursor.fetchone()[0]}')

# Count investments
cursor.execute('SELECT COUNT(*) FROM investments')
print(f'Investments: {cursor.fetchone()[0]}')

# Count custom categories
cursor.execute('SELECT COUNT(*) FROM custom_categories')
print(f'Custom Categories: {cursor.fetchone()[0]}')

# Count binance credentials
cursor.execute('SELECT COUNT(*) FROM binance_credentials')
print(f'Binance Credentials: {cursor.fetchone()[0]}')

# Show users
print('\n=== USERS ===')
cursor.execute('SELECT id, username, role FROM users')
for user in cursor.fetchall():
    print(f'ID: {user[0]}, Username: {user[1]}, Role: {user[2]}')

# Show total expenses per user
print('\n=== TOTAL EXPENSES PER USER ===')
cursor.execute('''
    SELECT u.username, COUNT(e.id) as expense_count, SUM(e.amount) as total_amount
    FROM users u
    LEFT JOIN expenses e ON u.id = e.user_id
    GROUP BY u.username
''')
for row in cursor.fetchall():
    total = row[2] if row[2] else 0
    print(f'{row[0]}: {row[1]} expenses, Total: ${total:.2f}')

conn.close()
print('\n✅ Verification complete!')
