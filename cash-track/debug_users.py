"""Debug user authentication in Railway"""
import psycopg2
from werkzeug.security import check_password_hash

RAILWAY_DATABASE_URL = 'postgresql://postgres:eMcCzPWdkacleqMeFBnqNGYoNnQmvEwF@hopper.proxy.rlwy.net:22426/railway'

conn = psycopg2.connect(RAILWAY_DATABASE_URL)
cursor = conn.cursor()

print('=== USERS IN RAILWAY DATABASE ===\n')

cursor.execute('SELECT id, username, password, role FROM users')
users = cursor.fetchall()

for user in users:
    user_id, username, password_hash, role = user
    print(f'ID: {user_id}')
    print(f'Username: {username}')
    print(f'Role: {role}')
    print(f'Password Hash: {password_hash[:50]}...')
    print(f'Hash starts with: {password_hash[:20]}')

    # Test passwords
    if username == 'pedromesaglio05@gmail.com':
        test_pass = 'Nilo2020!'
        result = check_password_hash(password_hash, test_pass)
        print(f'Password "Nilo2020!" matches: {result}')
    elif username == 'claramesaglio@gmail.com':
        test_pass = 'Nilo2020'
        result = check_password_hash(password_hash, test_pass)
        print(f'Password "Nilo2020" matches: {result}')
    elif username == 'admin':
        test_pass = 'admin'
        result = check_password_hash(password_hash, test_pass)
        print(f'Password "admin" matches: {result}')

    print('-' * 60)
    print()

conn.close()
