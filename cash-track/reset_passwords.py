"""Reset passwords for users in Railway database"""
import psycopg2
from werkzeug.security import generate_password_hash

RAILWAY_DATABASE_URL = 'postgresql://postgres:eMcCzPWdkacleqMeFBnqNGYoNnQmvEwF@hopper.proxy.rlwy.net:22426/railway'

# New passwords
passwords = {
    'pedromesaglio05@gmail.com': 'Nilo2020!',
    'claramesaglio@gmail.com': 'Nilo2020'
}

conn = psycopg2.connect(RAILWAY_DATABASE_URL)
cursor = conn.cursor()

print('=== RESETTING PASSWORDS ===\n')

for username, password in passwords.items():
    # Generate password hash
    hashed_password = generate_password_hash(password)

    # Update password
    cursor.execute(
        "UPDATE users SET password = %s WHERE username = %s",
        (hashed_password, username)
    )

    print(f'✅ Password updated for: {username}')

conn.commit()
conn.close()

print('\n✅ All passwords reset successfully!')
print('\nYou can now login with:')
for username, password in passwords.items():
    print(f'  - Username: {username}')
    print(f'    Password: {password}')
    print()
