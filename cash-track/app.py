from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_db, init_db
from datetime import datetime
import csv
import io
from functools import wraps
import ollama
import json
from price_api import PriceAPI, get_exchange_rate_usd_ars
from binance_api import BinanceIntegration, get_binance_client_for_user

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# Initialize database
init_db()

# Custom filter for formatting numbers with dots as thousand separators
@app.template_filter('format_number')
def format_number(value):
    """Format number with dots as thousand separators"""
    return '{:,.0f}'.format(value).replace(',', '.')

# Categories and payment methods
CATEGORIES = ['Alimentación', 'Transporte', 'Salud', 'Entretenimiento', 'Servicios', 'Educación', 'Ropa', 'Otros']
PAYMENT_METHODS = ['Efectivo', 'Tarjeta de Débito', 'Tarjeta de Crédito', 'Transferencia', 'Otros']
INVESTMENT_PLATFORMS = ['Binance', 'Bull Market', 'Invertir Online', 'Kraken', 'Coinbase', 'Mercado Pago', 'Ualá', 'Brubank', 'Otros']

def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('No tienes permisos para acceder a esta página', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    """Home page with summary"""
    conn = get_db()
    cursor = conn.cursor()

    # Get filter parameters
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    user_id = session['user_id']

    # Total expenses for the month
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) as total
        FROM expenses
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
    ''', (user_id, str(year), f'{month:02d}'))
    total_expenses = cursor.fetchone()['total']

    # Total income for the month
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) as total
        FROM income
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
    ''', (user_id, str(year), f'{month:02d}'))
    total_income = cursor.fetchone()['total']

    # Balance
    balance = total_income - total_expenses

    # Expenses by category
    cursor.execute('''
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        GROUP BY category
        ORDER BY total DESC
    ''', (user_id, str(year), f'{month:02d}'))
    expenses_by_category = cursor.fetchall()

    # Recent expenses
    cursor.execute('''
        SELECT * FROM expenses
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        ORDER BY date DESC, created_at DESC
        LIMIT 10
    ''', (user_id, str(year), f'{month:02d}'))
    recent_expenses = cursor.fetchall()

    # Recent income
    cursor.execute('''
        SELECT * FROM income
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        ORDER BY date DESC, created_at DESC
        LIMIT 10
    ''', (user_id, str(year), f'{month:02d}'))
    recent_income = cursor.fetchall()

    # Total investments
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) as total_invested,
               COALESCE(SUM(COALESCE(current_value, amount)), 0) as total_current
        FROM investments
        WHERE user_id = ?
    ''', (user_id,))
    investments_totals = cursor.fetchone()

    total_invested = investments_totals['total_invested']
    total_current = investments_totals['total_current']
    investment_profit = total_current - total_invested

    conn.close()

    return render_template('index.html',
                          total_expenses=total_expenses,
                          total_income=total_income,
                          balance=balance,
                          total_invested=total_invested,
                          total_current=total_current,
                          investment_profit=investment_profit,
                          expenses_by_category=expenses_by_category,
                          recent_expenses=recent_expenses,
                          recent_income=recent_income,
                          year=year,
                          month=month,
                          current_year=datetime.now().year,
                          current_month=datetime.now().month)

def get_all_categories(user_id):
    """Get all categories (default + custom)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT name, icon FROM custom_categories WHERE user_id = ? ORDER BY name', (user_id,))
    custom_cats = cursor.fetchall()
    conn.close()

    # Combine default categories with custom ones
    all_categories = CATEGORIES.copy()
    for cat in custom_cats:
        if cat['name'] not in all_categories:
            all_categories.append(cat['name'])

    return all_categories

def get_category_icons(user_id):
    """Get icons for all categories"""
    default_icons = {
        'Alimentación': '🍽️',
        'Transporte': '🚗',
        'Salud': '⚕️',
        'Entretenimiento': '🎉',
        'Servicios': '🏠',
        'Educación': '📚',
        'Ropa': '👕',
        'Otros': '📦'
    }

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT name, icon FROM custom_categories WHERE user_id = ?', (user_id,))
    custom_cats = cursor.fetchall()
    conn.close()

    # Add custom category icons
    for cat in custom_cats:
        default_icons[cat['name']] = cat['icon']

    return default_icons

@app.route('/expenses', methods=['GET', 'POST'])
@login_required
def expenses():
    """Manage expenses"""
    if request.method == 'POST':
        date = request.form['date']
        category = request.form['category']
        description = request.form['description']
        payment_method = request.form['payment_method']
        amount = float(request.form['amount'])

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO expenses (user_id, date, category, description, payment_method, amount)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], date, category, description, payment_method, amount))
        conn.commit()
        conn.close()

        flash('Gasto agregado exitosamente', 'success')
        return redirect(url_for('expenses'))

    # GET request - show form and list
    conn = get_db()
    cursor = conn.cursor()

    # Get filter parameters
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    cursor.execute('''
        SELECT * FROM expenses
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        ORDER BY date DESC, created_at DESC
    ''', (session['user_id'], str(year), f'{month:02d}'))
    all_expenses = cursor.fetchall()

    # Get custom categories for management (before closing connection)
    cursor.execute('SELECT id, name, icon FROM custom_categories WHERE user_id = ? ORDER BY name', (session['user_id'],))
    custom_categories = cursor.fetchall()

    conn.close()

    all_categories = get_all_categories(session['user_id'])
    category_icons = get_category_icons(session['user_id'])

    return render_template('expenses.html',
                          expenses=all_expenses,
                          categories=all_categories,
                          category_icons=category_icons,
                          custom_categories=custom_categories,
                          payment_methods=PAYMENT_METHODS,
                          year=year,
                          month=month,
                          current_year=datetime.now().year,
                          current_month=datetime.now().month)

@app.route('/income', methods=['GET', 'POST'])
@login_required
def income():
    """Manage income"""
    if request.method == 'POST':
        date = request.form['date']
        source = request.form['source']
        amount = float(request.form['amount'])

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO income (user_id, date, source, amount)
            VALUES (?, ?, ?, ?)
        ''', (session['user_id'], date, source, amount))
        conn.commit()
        conn.close()

        flash('Ingreso agregado exitosamente', 'success')
        return redirect(url_for('income'))

    # GET request - show form and list
    conn = get_db()
    cursor = conn.cursor()

    # Get filter parameters
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    cursor.execute('''
        SELECT * FROM income
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        ORDER BY date DESC, created_at DESC
    ''', (session['user_id'], str(year), f'{month:02d}'))
    all_income = cursor.fetchall()
    conn.close()

    return render_template('income.html',
                          income=all_income,
                          year=year,
                          month=month,
                          current_year=datetime.now().year,
                          current_month=datetime.now().month)

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    """Delete an expense"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM expenses WHERE id = ? AND user_id = ?',
                   (expense_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Gasto eliminado', 'success')
    return redirect(url_for('expenses'))

@app.route('/delete_income/<int:income_id>', methods=['POST'])
@login_required
def delete_income(income_id):
    """Delete an income"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM income WHERE id = ? AND user_id = ?',
                   (income_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Ingreso eliminado', 'success')
    return redirect(url_for('income'))

@app.route('/add_category', methods=['POST'])
@login_required
def add_category():
    """Add a custom category"""
    category_name = request.form.get('category_name', '').strip()
    category_icon = request.form.get('category_icon', '📦').strip()

    if not category_name:
        flash('El nombre de la categoría es requerido', 'danger')
        return redirect(url_for('expenses'))

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            'INSERT INTO custom_categories (user_id, name, icon) VALUES (?, ?, ?)',
            (session['user_id'], category_name, category_icon)
        )
        conn.commit()
        flash(f'Categoría "{category_name}" agregada exitosamente', 'success')
    except Exception as e:
        flash('Esta categoría ya existe', 'danger')
    finally:
        conn.close()

    return redirect(url_for('expenses'))

@app.route('/delete_category/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    """Delete a custom category"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM custom_categories WHERE id = ? AND user_id = ?',
                   (category_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Categoría eliminada', 'success')
    return redirect(url_for('expenses'))

@app.route('/export_csv')
@login_required
def export_csv():
    """Export data to CSV"""
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    conn = get_db()
    cursor = conn.cursor()

    # Get expenses
    cursor.execute('''
        SELECT date, category, description, payment_method, amount
        FROM expenses
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        ORDER BY date DESC
    ''', (session['user_id'], str(year), f'{month:02d}'))
    expenses_data = cursor.fetchall()

    # Get income
    cursor.execute('''
        SELECT date, source, amount
        FROM income
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        ORDER BY date DESC
    ''', (session['user_id'], str(year), f'{month:02d}'))
    income_data = cursor.fetchall()

    conn.close()

    # Create CSV
    output = io.StringIO()

    # Write expenses
    output.write(f'GASTOS - {month:02d}/{year}\n')
    writer = csv.writer(output)
    writer.writerow(['Fecha', 'Categoría', 'Descripción', 'Medio de Pago', 'Monto'])
    for expense in expenses_data:
        writer.writerow([expense['date'], expense['category'], expense['description'],
                        expense['payment_method'], expense['amount']])

    output.write('\n')

    # Write income
    output.write(f'INGRESOS - {month:02d}/{year}\n')
    writer.writerow(['Fecha', 'Fuente', 'Monto'])
    for inc in income_data:
        writer.writerow([inc['date'], inc['source'], inc['amount']])

    # Create file
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'cashtrack_{year}_{month:02d}.csv'
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f'Bienvenido, {username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register page"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()

        try:
            cursor.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, generate_password_hash(password))
            )
            conn.commit()
            flash('Usuario registrado exitosamente. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('El usuario ya existe', 'danger')
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/investments', methods=['GET', 'POST'])
@login_required
def investments():
    """Manage investments"""
    if request.method == 'POST':
        date = request.form['date']
        inv_type = request.form['type']
        name = request.form['name']
        amount = float(request.form['amount'])
        current_value = request.form.get('current_value')
        if current_value:
            current_value = float(current_value)
        notes = request.form.get('notes', '')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO investments (user_id, date, type, name, amount, current_value, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], date, inv_type, name, amount, current_value, notes))
        conn.commit()
        conn.close()

        flash('Inversión agregada exitosamente', 'success')
        return redirect(url_for('investments'))

    # GET request - show form and list
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM investments
        WHERE user_id = ?
        ORDER BY date DESC, created_at DESC
    ''', (session['user_id'],))
    all_investments = cursor.fetchall()

    # Calculate total invested and current value
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) as total_invested,
               COALESCE(SUM(COALESCE(current_value, amount)), 0) as total_current
        FROM investments
        WHERE user_id = ?
    ''', (session['user_id'],))
    totals = cursor.fetchone()

    conn.close()

    # Check if user has Binance credentials
    creds = BinanceIntegration.get_user_credentials(session['user_id'])
    has_binance_credentials = creds is not None
    is_testnet = creds.get('is_testnet', False) if creds else False

    # Get Binance balances if user has credentials
    binance_balances = None
    binance_total_usd = 0
    binance_total_ars = 0
    exchange_rate = 0

    if has_binance_credentials:
        try:
            binance_client = get_binance_client_for_user(session['user_id'])
            if binance_client:
                balances = binance_client.get_account_balance()

                if balances:
                    exchange_rate = get_exchange_rate_usd_ars()
                    binance_balances = []

                    for balance in balances:
                        symbol = balance['asset']
                        price_usd = binance_client.get_crypto_price(symbol)

                        if price_usd:
                            balance['price_usd'] = price_usd
                            balance['price_ars'] = price_usd * exchange_rate
                            balance['total_usd'] = price_usd * balance['total']
                            balance['total_ars'] = price_usd * exchange_rate * balance['total']

                            binance_total_usd += balance['total_usd']
                            binance_total_ars += balance['total_ars']
                        else:
                            balance['price_usd'] = 0
                            balance['price_ars'] = 0
                            balance['total_usd'] = 0
                            balance['total_ars'] = 0

                        binance_balances.append(balance)
        except Exception as e:
            print(f"Error obteniendo balances de Binance: {e}")
            binance_balances = None

    return render_template('investments.html',
                          investments=all_investments,
                          investment_platforms=INVESTMENT_PLATFORMS,
                          total_invested=totals['total_invested'],
                          total_current=totals['total_current'],
                          has_binance_credentials=has_binance_credentials,
                          is_testnet=is_testnet,
                          binance_balances=binance_balances,
                          binance_total_usd=binance_total_usd,
                          binance_total_ars=binance_total_ars,
                          exchange_rate=exchange_rate)

@app.route('/delete_investment/<int:investment_id>', methods=['POST'])
@login_required
def delete_investment(investment_id):
    """Delete an investment"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM investments WHERE id = ? AND user_id = ?',
                   (investment_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Inversión eliminada', 'success')
    return redirect(url_for('investments'))

@app.route('/update_investment_prices', methods=['POST'])
@login_required
def update_investment_prices():
    """Actualiza los precios de las inversiones con APIs en tiempo real"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Verificar si hay credenciales de Binance
        binance_client = get_binance_client_for_user(session['user_id'])

        # Obtener tasa de cambio
        exchange_rate = get_exchange_rate_usd_ars()

        # Obtener inversiones del usuario que tengan símbolo
        cursor.execute('''
            SELECT id, type, symbol, amount, name
            FROM investments
            WHERE user_id = ? AND symbol IS NOT NULL AND symbol != ''
        ''', (session['user_id'],))

        investments = cursor.fetchall()

        api = PriceAPI()
        updated_count = 0
        errors = []

        for inv in investments:
            inv_id = inv['id']
            inv_type = inv['type']
            symbol = inv['symbol']
            original_amount = inv['amount']

            # Si es Binance y tenemos cliente configurado, usar Binance API
            if inv_type == 'Binance' and binance_client:
                price_usd = binance_client.get_crypto_price(symbol)
                if price_usd:
                    price_ars = price_usd * exchange_rate
                    cursor.execute('''
                        UPDATE investments
                        SET current_value = ?
                        WHERE id = ?
                    ''', (price_ars, inv_id))
                    updated_count += 1
                else:
                    errors.append(f"{inv['name']} ({symbol})")
            else:
                # Usar APIs públicas para otros casos
                price_per_unit = api.get_asset_price(inv_type, symbol, exchange_rate)

                if price_per_unit:
                    cursor.execute('''
                        UPDATE investments
                        SET current_value = ?
                        WHERE id = ?
                    ''', (price_per_unit, inv_id))
                    updated_count += 1
                else:
                    errors.append(f"{inv['name']} ({symbol})")

        conn.commit()
        conn.close()

        if updated_count > 0:
            flash(f'✅ {updated_count} inversión(es) actualizada(s) con precios en tiempo real', 'success')

        if errors:
            flash(f'⚠️ No se pudieron actualizar: {", ".join(errors)}', 'warning')

        return redirect(url_for('investments'))

    except Exception as e:
        flash(f'❌ Error actualizando precios: {str(e)}', 'danger')
        return redirect(url_for('investments'))

# Binance Configuration Routes
@app.route('/binance/config', methods=['GET'])
@login_required
def binance_config():
    """Binance configuration page"""
    creds = BinanceIntegration.get_user_credentials(session['user_id'])

    has_credentials = creds is not None
    is_testnet = creds.get('is_testnet', False) if creds else False

    return render_template('binance_config.html',
                          has_credentials=has_credentials,
                          is_testnet=is_testnet)

@app.route('/binance/save-credentials', methods=['POST'])
@login_required
def save_binance_credentials():
    """Save Binance API credentials"""
    api_key = request.form.get('api_key', '').strip()
    api_secret = request.form.get('api_secret', '').strip()
    is_testnet = request.form.get('is_testnet') == '1'

    if not api_key or not api_secret:
        flash('API Key y API Secret son requeridos', 'danger')
        return redirect(url_for('binance_config'))

    # Probar la conexión antes de guardar
    try:
        test_client = BinanceIntegration(api_key, api_secret, is_testnet)
        if not test_client.test_connection():
            flash('❌ No se pudo conectar con Binance. Verifica tus credenciales', 'danger')
            return redirect(url_for('binance_config'))
    except Exception as e:
        flash(f'❌ Error probando conexión: {str(e)}', 'danger')
        return redirect(url_for('binance_config'))

    # Guardar credenciales
    if BinanceIntegration.save_credentials(session['user_id'], api_key, api_secret, is_testnet):
        flash('✅ Credenciales de Binance guardadas exitosamente', 'success')
    else:
        flash('❌ Error guardando credenciales', 'danger')

    return redirect(url_for('binance_config'))

@app.route('/binance/delete-credentials', methods=['POST'])
@login_required
def delete_binance_credentials():
    """Delete Binance API credentials"""
    if BinanceIntegration.delete_credentials(session['user_id']):
        flash('✅ Credenciales eliminadas exitosamente', 'success')
    else:
        flash('❌ Error eliminando credenciales', 'danger')

    return redirect(url_for('binance_config'))

@app.route('/binance/test-connection')
@login_required
def test_binance_connection():
    """Test Binance API connection"""
    binance_client = get_binance_client_for_user(session['user_id'])

    if not binance_client:
        flash('❌ No tienes credenciales de Binance configuradas', 'warning')
        return redirect(url_for('binance_config'))

    if binance_client.test_connection():
        flash('✅ Conexión con Binance exitosa', 'success')
    else:
        flash('❌ Error en la conexión con Binance', 'danger')

    return redirect(url_for('binance_config'))

@app.route('/binance/balances')
@login_required
def binance_balances():
    """View Binance account balances"""
    binance_client = get_binance_client_for_user(session['user_id'])

    if not binance_client:
        flash('❌ No tienes credenciales de Binance configuradas', 'warning')
        return redirect(url_for('binance_config'))

    balances = binance_client.get_account_balance()

    if balances is None:
        flash('❌ Error obteniendo balances de Binance', 'danger')
        return redirect(url_for('binance_config'))

    # Obtener precios en ARS para cada activo
    exchange_rate = get_exchange_rate_usd_ars()

    for balance in balances:
        symbol = balance['asset']
        price_usd = binance_client.get_crypto_price(symbol)

        if price_usd:
            balance['price_usd'] = price_usd
            balance['price_ars'] = price_usd * exchange_rate
            balance['total_usd'] = price_usd * balance['total']
            balance['total_ars'] = price_usd * exchange_rate * balance['total']
        else:
            balance['price_usd'] = 0
            balance['price_ars'] = 0
            balance['total_usd'] = 0
            balance['total_ars'] = 0

    return render_template('binance_balances.html',
                          balances=balances,
                          exchange_rate=exchange_rate)

@app.route('/binance/sync-to-investments', methods=['POST'])
@login_required
def sync_binance_to_investments():
    """Sync Binance balances to investments"""
    binance_client = get_binance_client_for_user(session['user_id'])

    if not binance_client:
        flash('❌ No tienes credenciales de Binance configuradas', 'warning')
        return redirect(url_for('binance_config'))

    balances = binance_client.get_account_balance()

    if balances is None:
        flash('❌ Error obteniendo balances de Binance', 'danger')
        return redirect(url_for('binance_balances'))

    # Obtener tasa de cambio
    exchange_rate = get_exchange_rate_usd_ars()

    conn = get_db()
    cursor = conn.cursor()

    synced_count = 0
    updated_count = 0

    for balance in balances:
        symbol = balance['asset']
        total_amount = balance['total']

        # Obtener precio en ARS
        price_usd = binance_client.get_crypto_price(symbol)
        if not price_usd:
            continue

        price_ars = price_usd * exchange_rate
        total_value_ars = price_ars * total_amount

        # Verificar si ya existe esta inversión
        cursor.execute('''
            SELECT id FROM investments
            WHERE user_id = ? AND type = 'Binance' AND symbol = ?
        ''', (session['user_id'], symbol))

        existing = cursor.fetchone()

        if existing:
            # Actualizar inversión existente
            cursor.execute('''
                UPDATE investments
                SET amount = ?, current_value = ?, notes = ?, date = ?
                WHERE id = ?
            ''', (total_value_ars, total_value_ars,
                  f'Sincronizado desde Binance - {total_amount} {symbol}',
                  datetime.now().strftime('%Y-%m-%d'),
                  existing['id']))
            updated_count += 1
        else:
            # Crear nueva inversión
            cursor.execute('''
                INSERT INTO investments (user_id, date, type, name, amount, current_value, notes, symbol)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (session['user_id'],
                  datetime.now().strftime('%Y-%m-%d'),
                  'Binance',
                  f'{symbol} (Binance)',
                  total_value_ars,
                  total_value_ars,
                  f'Sincronizado desde Binance - {total_amount} {symbol}',
                  symbol))
            synced_count += 1

    conn.commit()
    conn.close()

    if synced_count > 0 or updated_count > 0:
        flash(f'✅ {synced_count} inversiones creadas, {updated_count} actualizadas desde Binance', 'success')
    else:
        flash('ℹ️ No hay balances para sincronizar', 'info')

    return redirect(url_for('investments'))

@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('login'))

# Admin Routes
@app.route('/admin/users')
@admin_required
def admin_users():
    """Admin panel - manage users"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, username, role, created_at,
               (SELECT COUNT(*) FROM expenses WHERE user_id = users.id) as expense_count,
               (SELECT COUNT(*) FROM income WHERE user_id = users.id) as income_count
        FROM users
        ORDER BY created_at DESC
    ''')
    users = cursor.fetchall()
    conn.close()

    return render_template('admin_users.html', users=users)

@app.route('/admin/users/change_role/<int:user_id>', methods=['POST'])
@admin_required
def admin_change_role(user_id):
    """Change user role"""
    new_role = request.form.get('role')

    if new_role not in ['user', 'admin']:
        flash('Rol inválido', 'danger')
        return redirect(url_for('admin_users'))

    conn = get_db()
    cursor = conn.cursor()

    # Prevent changing your own role
    if user_id == session['user_id']:
        flash('No puedes cambiar tu propio rol', 'warning')
        conn.close()
        return redirect(url_for('admin_users'))

    cursor.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
    conn.commit()
    conn.close()

    flash(f'Rol actualizado exitosamente', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    """Delete user and all their data"""
    # Prevent deleting yourself
    if user_id == session['user_id']:
        flash('No puedes eliminar tu propia cuenta', 'warning')
        return redirect(url_for('admin_users'))

    conn = get_db()
    cursor = conn.cursor()

    # Delete user's data (cascade will happen with foreign keys)
    cursor.execute('DELETE FROM expenses WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM income WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM investments WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM custom_categories WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))

    conn.commit()
    conn.close()

    flash('Usuario eliminado exitosamente', 'success')
    return redirect(url_for('admin_users'))

# AI Assistant Routes
@app.route('/ai/chat', methods=['POST'])
@login_required
def ai_chat():
    """Chat with AI financial assistant"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        # Get user's financial data
        conn = get_db()
        cursor = conn.cursor()
        user_id = session['user_id']

        # Get total expenses and income
        cursor.execute('SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE user_id = ?', (user_id,))
        total_expenses = cursor.fetchone()['total']

        cursor.execute('SELECT COALESCE(SUM(amount), 0) as total FROM income WHERE user_id = ?', (user_id,))
        total_income = cursor.fetchone()['total']

        # Get expenses by category
        cursor.execute('''
            SELECT category, SUM(amount) as total
            FROM expenses
            WHERE user_id = ?
            GROUP BY category
            ORDER BY total DESC
        ''', (user_id,))
        expenses_by_category = cursor.fetchall()

        # Get recent transactions
        cursor.execute('SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC LIMIT 5', (user_id,))
        recent_expenses = cursor.fetchall()

        conn.close()

        # Prepare context for AI
        context = f"""Eres un asesor financiero personal profesional pero cercano llamado "FinanceBot".
Tu objetivo es ayudar a personas a manejar mejor sus finanzas personales con consejos expertos pero accesibles.
Hablas en español de forma amigable y clara, combinando conocimiento profesional con un trato cercano.

Brindás consejos profesionales sobre:
- Optimización de gastos cotidianos (alimentación, transporte, entretenimiento)
- Planificación financiera personal
- Estrategias de ahorro realistas
- Gestión de presupuesto personal
- Balance entre calidad de vida y ahorro

Usá un lenguaje claro y profesional, pero evitá tecnicismos innecesarios. Tratá a la persona con respeto y cercanía.

Datos financieros personales:
- Total de ingresos: ${total_income:,.2f} ARS
- Total de gastos: ${total_expenses:,.2f} ARS
- Balance: ${total_income - total_expenses:,.2f} ARS

Tus gastos por categoría:
"""
        for cat in expenses_by_category:
            context += f"- {cat['category']}: ${cat['total']:,.2f} ARS\n"

        context += "\nTus últimos gastos:\n"
        for exp in recent_expenses:
            context += f"- {exp['date']}: {exp['description']} (${exp['amount']:,.2f}) - {exp['category']}\n"

        # Call Ollama API
        response = ollama.chat(
            model='llama3.2',
            messages=[
                {'role': 'system', 'content': context},
                {'role': 'user', 'content': user_message}
            ]
        )

        ai_response = response['message']['content']

        return jsonify({
            'response': ai_response,
            'success': True
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/ai/analyze', methods=['GET'])
@login_required
def ai_analyze():
    """Get AI analysis of spending patterns"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        user_id = session['user_id']

        # Get comprehensive financial data
        cursor.execute('SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE user_id = ?', (user_id,))
        total_expenses = cursor.fetchone()['total']

        cursor.execute('SELECT COALESCE(SUM(amount), 0) as total FROM income WHERE user_id = ?', (user_id,))
        total_income = cursor.fetchone()['total']

        cursor.execute('''
            SELECT category, SUM(amount) as total
            FROM expenses
            WHERE user_id = ?
            GROUP BY category
            ORDER BY total DESC
        ''', (user_id,))
        expenses_by_category = cursor.fetchall()

        conn.close()

        # Prepare analysis prompt
        prompt = f"""Analizá estas finanzas personales y brindá un análisis profesional pero claro (3-4 puntos clave):

Ingresos: ${total_income:,.2f} ARS
Gastos: ${total_expenses:,.2f} ARS
Balance: ${total_income - total_expenses:,.2f} ARS

Distribución de gastos:
"""
        for cat in expenses_by_category:
            percentage = (cat['total'] / total_expenses * 100) if total_expenses > 0 else 0
            prompt += f"- {cat['category']}: ${cat['total']:,.2f} ARS ({percentage:.1f}%)\n"

        prompt += "\nProporcioná insights profesionales sobre:\n1. Evaluación de la situación financiera actual\n2. Categorías con mayor impacto en el presupuesto\n3. Recomendaciones concretas para optimizar gastos\n4. Oportunidades de mejora en los hábitos financieros\n\nUsá un tono profesional pero accesible y claro."

        response = ollama.chat(
            model='llama3.2',
            messages=[
                {'role': 'system', 'content': 'Eres un asesor financiero profesional especializado en finanzas personales. Brindás análisis expertos de forma clara y accesible. Usás lenguaje profesional pero cercano, evitando jerga compleja innecesaria.'},
                {'role': 'user', 'content': prompt}
            ]
        )

        return jsonify({
            'analysis': response['message']['content'],
            'success': True
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/ai/suggest-category', methods=['POST'])
@login_required
def ai_suggest_category():
    """Suggest category for expense using AI"""
    try:
        data = request.get_json()
        description = data.get('description', '')

        if not description:
            return jsonify({'error': 'No description provided'}), 400

        # Get user's past categorizations for learning
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT description, category
            FROM expenses
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 20
        ''', (session['user_id'],))
        past_expenses = cursor.fetchall()
        conn.close()

        # Prepare context with user's history
        context = "Eres un asistente especializado en categorización de gastos personales. Basándote en el historial de categorizaciones del usuario, sugiere la categoría más apropiada de forma precisa.\n\n"
        context += "Categorías disponibles: Alimentación, Transporte, Salud, Entretenimiento, Servicios, Educación, Ropa, Otros\n\n"
        context += "Historial de categorizaciones:\n"

        for exp in past_expenses:
            context += f"- '{exp['description']}' → {exp['category']}\n"

        prompt = f"Para el gasto: '{description}', ¿qué categoría corresponde? Respondé SOLO con el nombre de la categoría, sin explicaciones adicionales."

        response = ollama.chat(
            model='llama3.2',
            messages=[
                {'role': 'system', 'content': context},
                {'role': 'user', 'content': prompt}
            ]
        )

        suggested_category = response['message']['content'].strip()

        return jsonify({
            'category': suggested_category,
            'success': True
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/ai/predict-expenses', methods=['GET'])
@login_required
def ai_predict_expenses():
    """Predict future expenses and provide alerts"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        user_id = session['user_id']

        # Get monthly expenses for the last 3 months
        cursor.execute('''
            SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
            FROM expenses
            WHERE user_id = ?
            GROUP BY month
            ORDER BY month DESC
            LIMIT 3
        ''', (user_id,))
        monthly_data = cursor.fetchall()

        # Get current month expenses
        current_month = datetime.now().strftime('%Y-%m')
        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0) as total
            FROM expenses
            WHERE user_id = ? AND strftime('%Y-%m', date) = ?
        ''', (user_id, current_month))
        current_month_total = cursor.fetchone()['total']

        # Get expenses by category this month
        cursor.execute('''
            SELECT category, SUM(amount) as total
            FROM expenses
            WHERE user_id = ? AND strftime('%Y-%m', date) = ?
            GROUP BY category
            ORDER BY total DESC
        ''', (user_id, current_month))
        current_categories = cursor.fetchall()

        conn.close()

        # Prepare prediction prompt
        prompt = f"""Analizá el patrón de gastos mensuales y brindá una predicción profesional para el mes actual:

Gastos de los últimos 3 meses:
"""
        for month_data in monthly_data:
            prompt += f"- {month_data['month']}: ${month_data['total']:,.2f} ARS\n"

        prompt += f"\nGastos acumulados del mes actual ({current_month}): ${current_month_total:,.2f} ARS\n\n"
        prompt += "Distribución por categoría este mes:\n"
        for cat in current_categories:
            prompt += f"- {cat['category']}: ${cat['total']:,.2f} ARS\n"

        prompt += "\n\nProporcioná:\n1. Proyección de gasto total para fin de mes\n2. Análisis de variaciones o gastos atípicos\n3. Recomendaciones para el resto del mes\n4. Comparativa con meses anteriores\n\nUsá un lenguaje profesional pero accesible."

        response = ollama.chat(
            model='llama3.2',
            messages=[
                {'role': 'system', 'content': 'Eres un analista financiero especializado en predicción de gastos personales. Brindás proyecciones y recomendaciones profesionales de forma clara y útil. Usás un tono experto pero accesible.'},
                {'role': 'user', 'content': prompt}
            ]
        )

        return jsonify({
            'prediction': response['message']['content'],
            'current_total': current_month_total,
            'success': True
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/ai/monthly-summary', methods=['GET'])
@login_required
def ai_monthly_summary():
    """Generate AI-powered monthly summary"""
    try:
        year = request.args.get('year', datetime.now().year, type=int)
        month = request.args.get('month', datetime.now().month, type=int)

        conn = get_db()
        cursor = conn.cursor()
        user_id = session['user_id']

        # Get month data
        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0) as total
            FROM expenses
            WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        ''', (user_id, str(year), f'{month:02d}'))
        total_expenses = cursor.fetchone()['total']

        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0) as total
            FROM income
            WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        ''', (user_id, str(year), f'{month:02d}'))
        total_income = cursor.fetchone()['total']

        cursor.execute('''
            SELECT category, SUM(amount) as total, COUNT(*) as count
            FROM expenses
            WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
            GROUP BY category
            ORDER BY total DESC
        ''', (user_id, str(year), f'{month:02d}'))
        expenses_by_category = cursor.fetchall()

        # Get top expenses
        cursor.execute('''
            SELECT description, amount, category, date
            FROM expenses
            WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
            ORDER BY amount DESC
            LIMIT 5
        ''', (user_id, str(year), f'{month:02d}'))
        top_expenses = cursor.fetchall()

        # Get previous month for comparison
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1

        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0) as total
            FROM expenses
            WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        ''', (user_id, str(prev_year), f'{prev_month:02d}'))
        prev_month_expenses = cursor.fetchone()['total']

        conn.close()

        # Prepare summary prompt
        month_names = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                       'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

        prompt = f"""Generá un resumen financiero profesional pero motivador para {month_names[month-1]} {year}:

RESUMEN FINANCIERO DEL MES:
- Ingresos: ${total_income:,.2f} ARS
- Gastos: ${total_expenses:,.2f} ARS
- Balance: ${total_income - total_expenses:,.2f} ARS
- Gastos mes anterior: ${prev_month_expenses:,.2f} ARS
- Variación: ${total_expenses - prev_month_expenses:,.2f} ARS ({((total_expenses - prev_month_expenses) / prev_month_expenses * 100) if prev_month_expenses > 0 else 0:.1f}%)

DISTRIBUCIÓN DE GASTOS:
"""
        for cat in expenses_by_category:
            percentage = (cat['total'] / total_expenses * 100) if total_expenses > 0 else 0
            prompt += f"- {cat['category']}: ${cat['total']:,.2f} ARS ({percentage:.1f}%) - {cat['count']} transacciones\n"

        prompt += "\nPRINCIPALES GASTOS DEL MES:\n"
        for exp in top_expenses:
            prompt += f"- {exp['date']}: {exp['description']} - ${exp['amount']:,.2f} ({exp['category']})\n"

        prompt += "\n\nGenerá un resumen que incluya:\n1. Título profesional y motivador\n2. Análisis de la situación financiera del mes\n3. Análisis de categorías principales\n4. Comparativa con mes anterior\n5. Aspectos positivos y áreas de mejora\n6. Recomendaciones estratégicas para el próximo mes\n\nUsá un tono profesional pero cercano y motivador."

        response = ollama.chat(
            model='llama3.2',
            messages=[
                {'role': 'system', 'content': 'Eres un asesor financiero profesional que genera resúmenes mensuales detallados y motivadores. Combinás análisis experto con un tono cercano y alentador. Usás lenguaje profesional pero accesible.'},
                {'role': 'user', 'content': prompt}
            ]
        )

        return jsonify({
            'summary': response['message']['content'],
            'data': {
                'total_income': total_income,
                'total_expenses': total_expenses,
                'balance': total_income - total_expenses,
                'month': month_names[month-1],
                'year': year
            },
            'success': True
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=9000)
