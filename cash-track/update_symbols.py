#!/usr/bin/env python3
"""Script para actualizar los símbolos de las inversiones existentes"""
from database import get_db

def update_investment_symbols():
    """Actualiza los símbolos de las inversiones existentes"""
    conn = get_db()
    cursor = conn.cursor()

    # Bitcoin
    cursor.execute('''
        UPDATE investments
        SET symbol = 'BTC'
        WHERE (name LIKE '%Bitcoin%' OR name LIKE '%BTC%') AND symbol IS NULL
    ''')

    # Ethereum
    cursor.execute('''
        UPDATE investments
        SET symbol = 'ETH'
        WHERE (name LIKE '%Ethereum%' OR name LIKE '%ETH%') AND symbol IS NULL
    ''')

    # Apple
    cursor.execute('''
        UPDATE investments
        SET symbol = 'AAPL'
        WHERE (name LIKE '%AAPL%' OR name LIKE '%Apple%') AND symbol IS NULL
    ''')

    conn.commit()

    # Mostrar actualiz aciones
    cursor.execute('SELECT id, name, symbol, type FROM investments')
    investments = cursor.fetchall()

    print("✅ Símbolos actualizados:\n")
    for inv in investments:
        symbol_text = inv['symbol'] if inv['symbol'] else '❌ Sin símbolo'
        print(f"  [{inv['type']}] {inv['name']} → {symbol_text}")

    conn.close()

if __name__ == '__main__':
    update_investment_symbols()
