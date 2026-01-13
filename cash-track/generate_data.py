import sqlite3
from datetime import datetime, timedelta
import random

DATABASE = 'cashtrack.db'

def clear_existing_data():
    """Limpia los datos existentes del usuario admin"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('DELETE FROM expenses WHERE user_id = 1')
    cursor.execute('DELETE FROM income WHERE user_id = 1')

    conn.commit()
    conn.close()
    print("🗑️  Datos anteriores eliminados")

def generate_vacation_data():
    # Limpiar datos anteriores
    clear_existing_data()

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Usuario admin (ID = 1)
    user_id = 1

    # Cotización dólar (aproximada para Argentina 2026)
    USD_TO_ARS = 1500

    # Fecha base - Enero 2026
    base_date = datetime(2026, 1, 1)

    print("🌟 Generando datos de vacaciones en Argentina...")
    print(f"💵 Cotización USD: ${USD_TO_ARS} ARS\n")

    # ==================== INGRESO ====================
    # Cobro de salario en dólares convertido a pesos
    salario_usd = 900
    salario_ars = salario_usd * USD_TO_ARS

    cursor.execute('''
        INSERT INTO income (user_id, date, source, amount)
        VALUES (?, ?, ?, ?)
    ''', (user_id, base_date.strftime('%Y-%m-%d'), 'Salario Enero (900 USD)', salario_ars))
    print(f"✅ Ingreso: ${salario_ars:,.0f} ARS - Salario Enero (900 USD)")

    # ==================== GASTOS PREVIOS AL VIAJE ====================
    # Preparativos (precios en pesos argentinos)
    expenses_prep = [
        (base_date + timedelta(days=2), 'Ropa', 'Traje de baño nuevo', 'Tarjeta de Crédito', 25000),
        (base_date + timedelta(days=2), 'Ropa', 'Sandalias de playa', 'Tarjeta de Crédito', 15000),
        (base_date + timedelta(days=3), 'Salud', 'Protector solar SPF 50', 'Efectivo', 12000),
        (base_date + timedelta(days=3), 'Otros', 'Mochila para viaje', 'Tarjeta de Débito', 28000),
        (base_date + timedelta(days=4), 'Alimentación', 'Snacks para el viaje', 'Efectivo', 8000),
    ]

    for date, category, description, payment_method, amount in expenses_prep:
        cursor.execute('''
            INSERT INTO expenses (user_id, date, category, description, payment_method, amount)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, date.strftime('%Y-%m-%d'), category, description, payment_method, amount))
        print(f"✅ Gasto: ${amount:,.0f} ARS - {description}")

    # ==================== VIAJE A PUNTA DEL ESTE ====================
    print("\n🏖️  PUNTA DEL ESTE")

    # Día 1 - Llegada a Punta del Este (5 de enero)
    pde_day1 = base_date + timedelta(days=5)

    expenses_pde = [
        # Transporte
        (pde_day1, 'Transporte', 'Bus a Punta del Este', 'Tarjeta de Débito', 55000),
        (pde_day1, 'Transporte', 'Taxi del terminal al hospedaje', 'Efectivo', 6000),

        # Alojamiento
        (pde_day1, 'Servicios', 'Hospedaje Punta del Este - 3 noches', 'Tarjeta de Crédito', 105000),

        # Comidas Día 1
        (pde_day1, 'Alimentación', 'Almuerzo en La Barra', 'Tarjeta de Crédito', 18000),
        (pde_day1, 'Alimentación', 'Cena pizzería', 'Tarjeta de Crédito', 22000),
        (pde_day1, 'Alimentación', 'Helado artesanal', 'Efectivo', 4000),

        # Día 2 - Playa y paseos
        (pde_day1 + timedelta(days=1), 'Entretenimiento', 'Alquiler de sombrilla', 'Efectivo', 10000),
        (pde_day1 + timedelta(days=1), 'Alimentación', 'Desayuno cafetería', 'Efectivo', 6000),
        (pde_day1 + timedelta(days=1), 'Alimentación', 'Almuerzo en la playa', 'Efectivo', 15000),
        (pde_day1 + timedelta(days=1), 'Entretenimiento', 'Entrada museo Casapueblo', 'Tarjeta de Débito', 10000),
        (pde_day1 + timedelta(days=1), 'Alimentación', 'Cena parrillada', 'Tarjeta de Crédito', 25000),

        # Día 3 - Compras y actividades
        (pde_day1 + timedelta(days=2), 'Alimentación', 'Desayuno', 'Efectivo', 6000),
        (pde_day1 + timedelta(days=2), 'Ropa', 'Remera recuerdo Punta del Este', 'Tarjeta de Crédito', 15000),
        (pde_day1 + timedelta(days=2), 'Otros', 'Souvenirs para familia', 'Efectivo', 20000),
        (pde_day1 + timedelta(days=2), 'Alimentación', 'Almuerzo en puerto', 'Tarjeta de Débito', 20000),
        (pde_day1 + timedelta(days=2), 'Alimentación', 'Cena despedida', 'Tarjeta de Crédito', 24000),
    ]

    for date, category, description, payment_method, amount in expenses_pde:
        cursor.execute('''
            INSERT INTO expenses (user_id, date, category, description, payment_method, amount)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, date.strftime('%Y-%m-%d'), category, description, payment_method, amount))
        print(f"✅ Gasto: ${amount:,.0f} ARS - {description}")

    # ==================== VIAJE A TERMAS DE ORENSE ====================
    print("\n🌊 TERMAS DE ORENSE")

    # Viaje a Orense (10 de enero)
    orense_day1 = base_date + timedelta(days=10)

    expenses_orense = [
        # Transporte
        (orense_day1, 'Transporte', 'Bus Punta del Este a Orense', 'Tarjeta de Débito', 38000),

        # Alojamiento
        (orense_day1, 'Servicios', 'Hospedaje Termas de Orense - 2 noches', 'Tarjeta de Crédito', 80000),

        # Día 1 Orense
        (orense_day1, 'Alimentación', 'Almuerzo llegada', 'Efectivo', 15000),
        (orense_day1, 'Entretenimiento', 'Entrada complejo termal', 'Tarjeta de Crédito', 20000),
        (orense_day1, 'Alimentación', 'Cena restaurant', 'Tarjeta de Crédito', 20000),

        # Día 2 Orense - Relax
        (orense_day1 + timedelta(days=1), 'Alimentación', 'Desayuno', 'Efectivo', 8000),
        (orense_day1 + timedelta(days=1), 'Entretenimiento', 'Piscinas termales', 'Tarjeta de Crédito', 18000),
        (orense_day1 + timedelta(days=1), 'Alimentación', 'Almuerzo ligero', 'Efectivo', 13000),
        (orense_day1 + timedelta(days=1), 'Alimentación', 'Cena', 'Tarjeta de Crédito', 22000),

        # Día 3 - Regreso
        (orense_day1 + timedelta(days=2), 'Alimentación', 'Desayuno', 'Efectivo', 8000),
        (orense_day1 + timedelta(days=2), 'Otros', 'Productos termales', 'Tarjeta de Crédito', 22000),
        (orense_day1 + timedelta(days=2), 'Transporte', 'Bus Orense a casa', 'Tarjeta de Débito', 40000),
    ]

    for date, category, description, payment_method, amount in expenses_orense:
        cursor.execute('''
            INSERT INTO expenses (user_id, date, category, description, payment_method, amount)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, date.strftime('%Y-%m-%d'), category, description, payment_method, amount))
        print(f"✅ Gasto: ${amount:,.0f} ARS - {description}")

    # ==================== GASTOS POST-VIAJE Y MENSUALES ====================
    print("\n🏠 POST-VIAJE Y GASTOS DEL MES")

    post_trip = base_date + timedelta(days=14)

    expenses_post = [
        # Gastos post-viaje
        (post_trip, 'Alimentación', 'Compras supermercado', 'Tarjeta de Débito', 50000),
        (post_trip, 'Transporte', 'Recarga SUBE', 'Efectivo', 10000),
        (post_trip + timedelta(days=1), 'Servicios', 'Luz y agua', 'Transferencia', 35000),
        (post_trip + timedelta(days=2), 'Alimentación', 'Delivery comida', 'Tarjeta de Crédito', 14000),
        (post_trip + timedelta(days=3), 'Servicios', 'Internet y cable', 'Transferencia', 22000),
        (post_trip + timedelta(days=4), 'Alimentación', 'Almuerzo en restaurant', 'Tarjeta de Débito', 16000),
        (post_trip + timedelta(days=5), 'Transporte', 'Combustible', 'Tarjeta de Débito', 28000),
        (post_trip + timedelta(days=6), 'Alimentación', 'Compras semanales', 'Tarjeta de Débito', 38000),
        (post_trip + timedelta(days=8), 'Entretenimiento', 'Cine', 'Tarjeta de Crédito', 9000),
        (post_trip + timedelta(days=10), 'Salud', 'Farmacia', 'Efectivo', 13000),
        (post_trip + timedelta(days=12), 'Alimentación', 'Compras supermercado', 'Tarjeta de Débito', 45000),
        (post_trip + timedelta(days=14), 'Transporte', 'Recarga SUBE', 'Efectivo', 10000),
    ]

    for date, category, description, payment_method, amount in expenses_post:
        cursor.execute('''
            INSERT INTO expenses (user_id, date, category, description, payment_method, amount)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, date.strftime('%Y-%m-%d'), category, description, payment_method, amount))
        print(f"✅ Gasto: ${amount:,.0f} ARS - {description}")

    # Commit y cerrar
    conn.commit()

    # Mostrar resumen
    print("\n" + "="*50)
    print("📊 RESUMEN FINANCIERO")
    print("="*50)

    cursor.execute('SELECT SUM(amount) FROM income WHERE user_id = ?', (user_id,))
    total_income = cursor.fetchone()[0] or 0

    cursor.execute('SELECT SUM(amount) FROM expenses WHERE user_id = ?', (user_id,))
    total_expenses = cursor.fetchone()[0] or 0

    balance = total_income - total_expenses

    print(f"💰 Total Ingresos:  ${total_income:.2f}")
    print(f"💸 Total Gastos:    ${total_expenses:.2f}")
    print(f"{'📈' if balance >= 0 else '📉'} Balance:         ${balance:.2f}")
    print("="*50)

    # Gastos por categoría
    print("\n📋 GASTOS POR CATEGORÍA:")
    cursor.execute('''
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY total DESC
    ''', (user_id,))

    for row in cursor.fetchall():
        print(f"   {row[0]:<20} ${row[1]:>7.2f}")

    conn.close()
    print("\n✨ ¡Datos generados exitosamente!")

if __name__ == '__main__':
    generate_vacation_data()
