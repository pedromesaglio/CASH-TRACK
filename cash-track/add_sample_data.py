#!/usr/bin/env python3
"""
Script para agregar datos de ejemplo a la base de datos
"""
from database import get_db
from datetime import datetime, timedelta
import random

def add_sample_data():
    """Add sample financial data for user with ID 1 (admin)"""
    conn = get_db()
    cursor = conn.cursor()

    user_id = 1  # Admin user
    current_date = datetime.now()

    print("Agregando datos de ejemplo...")

    # Sample income data
    income_data = [
        ('2026-01-01', 'Salario Enero', 500000),
        ('2025-12-01', 'Salario Diciembre', 480000),
        ('2025-11-01', 'Salario Noviembre', 480000),
        ('2026-01-15', 'Freelance Proyecto Web', 120000),
        ('2025-12-20', 'Bonus Fin de Año', 80000),
    ]

    for date, source, amount in income_data:
        cursor.execute('''
            INSERT INTO income (user_id, date, source, amount)
            VALUES (?, ?, ?, ?)
        ''', (user_id, date, source, amount))

    print(f"✅ {len(income_data)} ingresos agregados")

    # Sample expense data
    expense_data = [
        # Alimentación
        ('2026-01-10', 'Alimentación', 'Supermercado semanal', 'Tarjeta de Débito', 35000),
        ('2026-01-05', 'Alimentación', 'Carrefour compras mensuales', 'Tarjeta de Crédito', 45000),
        ('2026-01-12', 'Alimentación', 'Pedido delivery pizza', 'Efectivo', 8500),
        ('2025-12-28', 'Alimentación', 'Cena familiar restaurante', 'Tarjeta de Crédito', 28000),

        # Transporte
        ('2026-01-08', 'Transporte', 'Carga SUBE', 'Transferencia', 5000),
        ('2026-01-11', 'Transporte', 'Uber al trabajo', 'Tarjeta de Débito', 3200),
        ('2025-12-15', 'Transporte', 'Service auto', 'Efectivo', 25000),

        # Salud
        ('2026-01-07', 'Salud', 'Obra social cuota mensual', 'Tarjeta de Débito', 12000),
        ('2025-12-20', 'Salud', 'Medicamentos farmacia', 'Efectivo', 4500),

        # Entretenimiento
        ('2026-01-09', 'Entretenimiento', 'Netflix suscripción', 'Tarjeta de Crédito', 3500),
        ('2026-01-06', 'Entretenimiento', 'Cine con amigos', 'Efectivo', 5000),
        ('2025-12-25', 'Entretenimiento', 'Regalos Navidad', 'Tarjeta de Crédito', 45000),

        # Servicios
        ('2026-01-05', 'Servicios', 'Luz - Edenor', 'Transferencia', 15000),
        ('2026-01-03', 'Servicios', 'Internet Fibra', 'Tarjeta de Débito', 8500),
        ('2025-12-28', 'Servicios', 'Gas Natural', 'Transferencia', 12000),

        # Educación
        ('2026-01-04', 'Educación', 'Curso online Udemy', 'Tarjeta de Crédito', 8900),
        ('2025-12-10', 'Educación', 'Libros técnicos', 'Efectivo', 12000),

        # Ropa
        ('2025-12-22', 'Ropa', 'Ropa verano', 'Tarjeta de Crédito', 35000),
        ('2026-01-11', 'Ropa', 'Zapatillas running', 'Tarjeta de Débito', 28000),
    ]

    for date, category, description, payment_method, amount in expense_data:
        cursor.execute('''
            INSERT INTO expenses (user_id, date, category, description, payment_method, amount)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, date, category, description, payment_method, amount))

    print(f"✅ {len(expense_data)} gastos agregados")

    # Sample investment data
    investment_data = [
        ('2025-11-15', 'Binance', 'Criptomonedas', 'Bitcoin BTC', 150000, 165000, 'Compra mensual BTC'),
        ('2025-12-01', 'Bull Market', 'Acciones', 'Cedear AAPL', 80000, 85000, 'Apple Inc.'),
        ('2025-10-20', 'Mercado Pago', 'Fondo Común', 'Fondo Renta Fija', 100000, 102500, 'Inversión conservadora'),
        ('2025-09-10', 'Binance', 'Criptomonedas', 'Ethereum ETH', 120000, 135000, 'Compra ETH'),
        ('2025-12-20', 'Invertir Online', 'Bonos', 'Bono Soberano', 75000, 73500, 'Bono AL30'),
    ]

    for date, platform, inv_type, name, amount, current_value, notes in investment_data:
        cursor.execute('''
            INSERT INTO investments (user_id, date, type, name, amount, current_value, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, date, inv_type, name, amount, current_value, notes))

    print(f"✅ {len(investment_data)} inversiones agregadas")

    conn.commit()
    conn.close()

    print("\n" + "="*50)
    print("✨ Datos de ejemplo agregados exitosamente!")
    print("="*50)
    print("\n📊 Resumen:")
    print(f"   • {len(income_data)} ingresos")
    print(f"   • {len(expense_data)} gastos")
    print(f"   • {len(investment_data)} inversiones")
    print("\n💡 Inicia sesión con: admin / admin")
    print("="*50)

if __name__ == '__main__':
    add_sample_data()
