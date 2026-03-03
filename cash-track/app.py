from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from database import get_db, init_db
from datetime import datetime
import csv
import io
from functools import wraps
import ollama
import json
from price_api import PriceAPI, get_exchange_rate_usd_ars
from binance_api import BinanceIntegration, get_binance_client_for_user
from dollar_scraper import get_dollar_rate_with_fallback
import pdfplumber
import os
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-this-in-production')

# Security headers
@app.after_request
def set_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Only add HSTS in production with HTTPS
    if not app.debug:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# Session configuration
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
# Set SESSION_COOKIE_SECURE = True in production with HTTPS
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'

# Upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Create upload folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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

    user_id = session['user_id']

    # Get filter parameters
    # If no filter is specified, try to find the most recent month with data
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    if year is None or month is None:
        # Find most recent month with expenses or income
        cursor.execute('''
            SELECT strftime('%Y', date) as year, strftime('%m', date) as month
            FROM (
                SELECT date FROM expenses WHERE user_id = ?
                UNION ALL
                SELECT date FROM income WHERE user_id = ?
            )
            ORDER BY date DESC
            LIMIT 1
        ''', (user_id, user_id))

        recent = cursor.fetchone()
        if recent:
            year = int(recent['year']) if year is None else year
            month = int(recent['month']) if month is None else month
        else:
            # No data, use current month
            year = datetime.now().year if year is None else year
            month = datetime.now().month if month is None else month

    # Get current dollar MEP rate
    dollar_mep_rate = get_dollar_rate_with_fallback()

    # Total ARS expenses for the month
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) as total
        FROM expenses
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        AND (currency = 'ARS' OR currency IS NULL)
    ''', (user_id, str(year), f'{month:02d}'))
    total_ars_expenses = cursor.fetchone()['total']

    # Total USD expenses for the month
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) as total
        FROM expenses
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        AND currency = 'USD'
    ''', (user_id, str(year), f'{month:02d}'))
    total_usd_expenses = cursor.fetchone()['total']

    # Convert USD expenses to ARS
    total_usd_expenses_in_ars = total_usd_expenses * dollar_mep_rate

    # Total expenses in ARS (including converted USD)
    total_expenses = total_ars_expenses + total_usd_expenses_in_ars

    # Total income for the month
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) as total
        FROM income
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
    ''', (user_id, str(year), f'{month:02d}'))
    total_income = cursor.fetchone()['total']

    # Balance (all in ARS)
    balance = total_income - total_expenses

    # Get previous month data for comparison
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1

    # Previous month ARS expenses
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) as total
        FROM expenses
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        AND (currency = 'ARS' OR currency IS NULL)
    ''', (user_id, str(prev_year), f'{prev_month:02d}'))
    prev_total_ars_expenses = cursor.fetchone()['total']

    # Previous month USD expenses
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) as total
        FROM expenses
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        AND currency = 'USD'
    ''', (user_id, str(prev_year), f'{prev_month:02d}'))
    prev_total_usd_expenses = cursor.fetchone()['total']

    # Convert previous month USD to ARS
    prev_total_usd_expenses_in_ars = prev_total_usd_expenses * dollar_mep_rate

    # Total previous month expenses in ARS
    prev_total_expenses = prev_total_ars_expenses + prev_total_usd_expenses_in_ars

    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) as total
        FROM income
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
    ''', (user_id, str(prev_year), f'{prev_month:02d}'))
    prev_total_income = cursor.fetchone()['total']

    # Calculate changes
    expense_change = total_expenses - prev_total_expenses
    income_change = total_income - prev_total_income
    balance_change = balance - (prev_total_income - prev_total_expenses)
    usd_expense_change = total_usd_expenses - prev_total_usd_expenses

    # Calculate percentages
    expense_change_pct = (expense_change / prev_total_expenses * 100) if prev_total_expenses > 0 else 0
    income_change_pct = (income_change / prev_total_income * 100) if prev_total_income > 0 else 0
    usd_expense_change_pct = (usd_expense_change / prev_total_usd_expenses * 100) if prev_total_usd_expenses > 0 else 0

    # Expenses by category
    cursor.execute('''
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        GROUP BY category
        ORDER BY total DESC
    ''', (user_id, str(year), f'{month:02d}'))
    expenses_by_category = cursor.fetchall()

    # Get all expenses grouped by category for detailed view
    cursor.execute('''
        SELECT * FROM expenses
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        ORDER BY category, date DESC, created_at DESC
    ''', (user_id, str(year), f'{month:02d}'))
    all_expenses_by_category = cursor.fetchall()

    # Group expenses by category in Python
    expenses_detail = {}
    for expense in all_expenses_by_category:
        cat = expense['category']
        if cat not in expenses_detail:
            expenses_detail[cat] = []
        expenses_detail[cat].append(expense)

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

    # Get last 6 months data for trend chart
    cursor.execute('''
        SELECT strftime('%Y-%m', date) as month,
               SUM(amount) as total
        FROM expenses
        WHERE user_id = ?
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
    ''', (user_id,))
    monthly_expenses = cursor.fetchall()

    cursor.execute('''
        SELECT strftime('%Y-%m', date) as month,
               SUM(amount) as total
        FROM income
        WHERE user_id = ?
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
    ''', (user_id,))
    monthly_income = cursor.fetchall()

    conn.close()

    return render_template('index.html',
                          total_expenses=total_expenses,
                          total_ars_expenses=total_ars_expenses,
                          total_usd_expenses=total_usd_expenses,
                          total_usd_expenses_in_ars=total_usd_expenses_in_ars,
                          dollar_mep_rate=dollar_mep_rate,
                          total_income=total_income,
                          balance=balance,
                          expense_change=expense_change,
                          income_change=income_change,
                          balance_change=balance_change,
                          expense_change_pct=expense_change_pct,
                          income_change_pct=income_change_pct,
                          usd_expense_change=usd_expense_change,
                          usd_expense_change_pct=usd_expense_change_pct,
                          total_invested=total_invested,
                          total_current=total_current,
                          investment_profit=investment_profit,
                          expenses_by_category=expenses_by_category,
                          expenses_detail=expenses_detail,
                          recent_expenses=recent_expenses,
                          recent_income=recent_income,
                          monthly_expenses=list(reversed(monthly_expenses)),
                          monthly_income=list(reversed(monthly_income)),
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
        currency = request.form.get('currency', 'ARS')  # Default to ARS if not provided

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO expenses (user_id, date, category, description, payment_method, amount, currency)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], date, category, description, payment_method, amount, currency))
        conn.commit()
        conn.close()

        flash('Gasto agregado exitosamente', 'success')
        return redirect(url_for('expenses'))

    # GET request - show form and list
    conn = get_db()
    cursor = conn.cursor()

    user_id = session['user_id']

    # Get filter parameters
    # If no filter is specified, try to find the most recent month with data
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    if year is None or month is None:
        # Find most recent month with expenses
        cursor.execute('''
            SELECT strftime('%Y', date) as year, strftime('%m', date) as month
            FROM expenses
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT 1
        ''', (user_id,))

        recent = cursor.fetchone()
        if recent:
            year = int(recent['year']) if year is None else year
            month = int(recent['month']) if month is None else month
        else:
            # No data, use current month
            year = datetime.now().year if year is None else year
            month = datetime.now().month if month is None else month

    cursor.execute('''
        SELECT * FROM expenses
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        ORDER BY date DESC, created_at DESC
    ''', (user_id, str(year), f'{month:02d}'))
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
                          current_month=datetime.now().month,
                          show_all=False)

@app.route('/expenses/all')
@login_required
def expenses_all():
    """Show all expenses without date filter"""
    conn = get_db()
    cursor = conn.cursor()

    # Get ALL expenses for the user
    cursor.execute('''
        SELECT * FROM expenses
        WHERE user_id = ?
        ORDER BY date DESC, created_at DESC
        LIMIT 100
    ''', (session['user_id'],))
    all_expenses = cursor.fetchall()

    # Get custom categories for management
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
                          year=None,
                          month=None,
                          current_year=datetime.now().year,
                          current_month=datetime.now().month,
                          show_all=True)

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

    user_id = session['user_id']

    # Get filter parameters
    # If no filter is specified, try to find the most recent month with data
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    if year is None or month is None:
        # Find most recent month with income
        cursor.execute('''
            SELECT strftime('%Y', date) as year, strftime('%m', date) as month
            FROM income
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT 1
        ''', (user_id,))

        recent = cursor.fetchone()
        if recent:
            year = int(recent['year']) if year is None else year
            month = int(recent['month']) if month is None else month
        else:
            # No data, use current month
            year = datetime.now().year if year is None else year
            month = datetime.now().month if month is None else month

    cursor.execute('''
        SELECT * FROM income
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        ORDER BY date DESC, created_at DESC
    ''', (user_id, str(year), f'{month:02d}'))
    all_income = cursor.fetchall()
    conn.close()

    return render_template('income.html',
                          income=all_income,
                          year=year,
                          month=month,
                          current_year=datetime.now().year,
                          current_month=datetime.now().month)

@app.route('/upload_expenses_pdf', methods=['POST'])
@login_required
def upload_expenses_pdf():
    """Upload PDF and return job ID for progress tracking"""
    if 'pdf_file' not in request.files:
        flash('No se seleccionó ningún archivo', 'danger')
        return redirect(url_for('expenses'))

    file = request.files['pdf_file']

    if file.filename == '':
        flash('No se seleccionó ningún archivo', 'danger')
        return redirect(url_for('expenses'))

    if file and file.filename.lower().endswith('.pdf'):
        try:
            # Save the file temporarily
            import uuid
            job_id = str(uuid.uuid4())
            filename = f"{job_id}_{secure_filename(file.filename)}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Store job metadata in a file
            job_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}.json")
            with open(job_file, 'w') as f:
                json.dump({
                    'filepath': filepath,
                    'user_id': session['user_id'],
                    'status': 'pending'
                }, f)

            # Return the processing page with job ID
            return render_template('pdf_processing.html', job_id=job_id)

        except Exception as e:
            flash(f'❌ Error subiendo el PDF: {str(e)}', 'danger')
            return redirect(url_for('expenses'))
    else:
        flash('Por favor sube un archivo PDF válido', 'danger')
        return redirect(url_for('expenses'))

@app.route('/process_pdf/<job_id>')
@login_required
def process_pdf_stream(job_id):
    """Stream processing progress"""
    def generate():
        # Load job data from file
        job_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}.json")

        if not os.path.exists(job_file):
            yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
            return

        with open(job_file, 'r') as f:
            job_data = json.load(f)

        filepath = job_data['filepath']
        user_id = job_data['user_id']

        try:
            # Step 1: Extract text
            yield f"data: {json.dumps({'progress': 10, 'message': 'Extrayendo texto del PDF...'})}\n\n"
            text = extract_text_from_pdf(filepath)

            # Step 1.5: Extract closing date AND cardholder name from PDF
            closing_date = None
            cardholder_name = None

            # First, extract cardholder name (appears near the beginning, after "Resumen")
            for idx, line in enumerate(text.split('\n')):
                # Look for name pattern (usually appears before address, after "Resumen")
                # In BBVA format: name appears as "LASTNAME FIRSTNAME" in capitals
                if idx < 50 and re.match(r'^[A-Z\s]{10,}$', line.strip()) and len(line.strip().split()) >= 2:
                    potential_name = line.strip()
                    # Validate it's a name (not a title or other text)
                    if potential_name not in ['RESUMEN', 'PREMIUM WORLD', 'VISA', 'TARJETAS DE CREDITO'] and 'BBVA' not in potential_name:
                        cardholder_name = potential_name
                        break

            # Extract closing date
            for line in text.split('\n'):
                # Look for "CIERRE ACTUAL" line
                if 'CIERRE ACTUAL' in line:
                    # Try to find a date in format DD-MMM-YY
                    match = re.search(r'(\d{2})-([A-Za-z]{3})-(\d{2})', line)
                    if match:
                        day = match.group(1)
                        month_abbr = match.group(2)
                        year = match.group(3)

                        # Convert Spanish month abbreviation to number
                        months = {
                            'Ene': '01', 'Feb': '02', 'Mar': '03', 'Abr': '04',
                            'May': '05', 'Jun': '06', 'Jul': '07', 'Ago': '08',
                            'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dic': '12'
                        }
                        month = months.get(month_abbr, '01')

                        # Assume 20XX for year
                        full_year = f"20{year}"
                        closing_date = f"{full_year}-{month}-{day}"
                        break

            # If no closing date found, use today
            if not closing_date:
                from datetime import datetime
                closing_date = datetime.now().strftime('%Y-%m-%d')

            # Create pattern to match cardholder's consumption sections
            if cardholder_name:
                yield f"data: {json.dumps({'progress': 15, 'message': f'Titular: {cardholder_name} | Cierre: {closing_date}'})}\n\n"
            else:
                yield f"data: {json.dumps({'progress': 15, 'message': f'Fecha de cierre: {closing_date}'})}\n\n"

            # Step 2: Find transactions ONLY from cardholder's sections
            yield f"data: {json.dumps({'progress': 20, 'message': 'Identificando transacciones del titular...'})}\n\n"
            lines = text.split('\n')
            consumption_lines = []
            in_consumption_section = False

            for line in lines:
                # Start section ONLY if it matches the cardholder's name
                if 'Consumos' in line and cardholder_name:
                    # Check if line contains the cardholder's name (words in any order)
                    name_words = cardholder_name.split()
                    if all(word.lower() in line.lower() for word in name_words):
                        in_consumption_section = True
                        continue

                # Stop at total or other sections
                if any(keyword in line for keyword in ['TOTAL CONSUMOS', 'Impuestos', 'Legales y avisos', 'SALDO ACTUAL', 'Sus pagos']):
                    in_consumption_section = False
                    continue

                # Capture transaction lines
                if in_consumption_section and line.strip():
                    if re.match(r'^\d{2}-[A-Za-z]{3}-\d{2}', line) and 'BONIF' not in line:
                        consumption_lines.append(line.strip())

            total_lines = len(consumption_lines)
            yield f"data: {json.dumps({'progress': 30, 'message': f'Encontradas {total_lines} transacciones. Procesando con IA...'})}\n\n"

            # Process in chunks (reduced to 10 for better reliability)
            chunk_size = 10
            all_expenses = []
            total_chunks = (total_lines - 1) // chunk_size + 1

            for chunk_idx in range(0, total_lines, chunk_size):
                current_chunk = (chunk_idx // chunk_size) + 1
                chunk = consumption_lines[chunk_idx:chunk_idx + chunk_size]

                progress = 30 + int((current_chunk / total_chunks) * 50)
                yield f"data: {json.dumps({'progress': progress, 'message': f'Procesando grupo {current_chunk} de {total_chunks}...'})}\n\n"

                transactions_text = '\n'.join(chunk)

                prompt = f"""Sos un experto en análisis de resúmenes de tarjetas de crédito BBVA Argentina.

Analizá CADA LÍNEA del siguiente listado de transacciones y devolvé ÚNICAMENTE un JSON array.

Transacciones:
{transactions_text}

Formato de cada línea:
FECHA DESCRIPCIÓN [C.XX/YY si tiene cuotas] NRO_CUPON MONTO [puede tener USD al final]

Para CADA transacción extraé:
- fecha: YYYY-MM-DD (año 2025 si dice "25", 2024 si dice "24")
- description: comercio/descripción (limpio, sin números de cupón)
- amount: monto NUMÉRICO del ÚLTIMO número antes de USD (si tiene) o último número de la línea
  * Si el monto tiene formato "1.234,56" convertilo a 1234.56
  * Si es negativo (descuento/bonificación) devolvelo como positivo
  * NUNCA uses comas ni puntos como separadores de miles, solo punto decimal
  * Ejemplos: "4.334,38" → 4334.38, "35.000,00" → 35000.00
- currency: "USD" SOLO si la palabra "USD" aparece EXPLÍCITAMENTE en la línea. Si NO tiene "USD", es "ARS"
- installment_number: "X/Y" desde "C.XX/YY", null si no tiene cuotas
- category: Alimentación, Transporte, Salud, Entretenimiento, Servicios, Educación, Ropa, Otros
- payment_method: "Tarjeta de Crédito"

CRÍTICO SOBRE MONEDA:
- Si ves "USD" en el texto → currency: "USD"
- Si NO ves "USD" en el texto → currency: "ARS"
- NO adivines la moneda por el monto o comercio
- Ejemplo con USD: "15-Dic-25 OPENAI *CHATGPT in1SeRCUCUSD 20,00 473963 20,00" → currency: "USD", amount: 20.00
- Ejemplo sin USD: "04-Dic-25 AUTOPISTAS DEL S 960004413131001 000001 4.334,38" → currency: "ARS", amount: 4334.38

Devolvé SOLO el JSON array sin texto adicional:
[{{"date":"2025-12-04","description":"AUTOPISTAS DEL S","amount":4334.38,"currency":"ARS","category":"Transporte","payment_method":"Tarjeta de Crédito","installment_number":null}}]
"""

                try:
                    response = ollama.chat(
                        model='mistral:7b',
                        messages=[
                            {'role': 'system', 'content': 'Devolvés SOLO JSON válido sin texto adicional.'},
                            {'role': 'user', 'content': prompt}
                        ],
                        options={
                            'num_predict': 5000,
                            'temperature': 0.1
                        }
                    )

                    ai_response = response['message']['content'].strip()
                    ai_response = re.sub(r'```json\s*', '', ai_response)
                    ai_response = re.sub(r'```\s*', '', ai_response)
                    ai_response = ai_response.strip()

                    chunk_expenses = json.loads(ai_response)

                    for expense in chunk_expenses:
                        required_keys = ['date', 'description', 'amount', 'category', 'payment_method', 'currency']
                        if all(key in expense for key in required_keys):
                            # Convert amount to float, handling both formats
                            amount_str = str(expense['amount'])
                            # Remove currency symbols and whitespace
                            amount_str = amount_str.replace('$', '').replace('ARS', '').replace('USD', '').strip()
                            # Handle Argentine format (1.234,56) and US format (1234.56)
                            if ',' in amount_str and '.' in amount_str:
                                # Argentine format: 1.234,56 -> remove dots, replace comma with dot
                                amount_str = amount_str.replace('.', '').replace(',', '.')
                            elif ',' in amount_str:
                                # Only comma: could be decimal separator
                                amount_str = amount_str.replace(',', '.')

                            try:
                                expense['amount'] = abs(float(amount_str))  # Use abs to handle negative amounts
                                expense['currency'] = expense['currency'].upper()
                                if 'installment_number' not in expense:
                                    expense['installment_number'] = None
                                all_expenses.append(expense)
                            except ValueError as e:
                                print(f"Error converting amount '{expense['amount']}' for expense: {expense.get('description', 'unknown')}: {e}")
                                continue

                except json.JSONDecodeError as e:
                    print(f"❌ JSON Error in chunk {current_chunk}: {e}")
                    print(f"AI Response was: {ai_response[:500]}")
                    continue
                except Exception as e:
                    print(f"❌ Error processing chunk {current_chunk}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

            # Step 3: Insert into database
            yield f"data: {json.dumps({'progress': 85, 'message': f'Guardando {len(all_expenses)} gastos en la base de datos...'})}\n\n"

            conn = get_db()
            cursor = conn.cursor()
            inserted_count = 0

            for expense in all_expenses:
                try:
                    # Use closing_date instead of original transaction date
                    cursor.execute('''
                        INSERT INTO expenses (user_id, date, category, description, payment_method, amount, currency, installment_number)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (user_id, closing_date, expense['category'],
                          expense['description'], expense['payment_method'], expense['amount'],
                          expense.get('currency', 'ARS'), expense.get('installment_number')))
                    inserted_count += 1
                except Exception as e:
                    print(f"Error insertando gasto: {e}")
                    continue

            conn.commit()
            conn.close()

            # Remove temporary files
            os.remove(filepath)
            if os.path.exists(job_file):
                os.remove(job_file)

            # Step 4: Complete
            yield f"data: {json.dumps({'progress': 100, 'message': f'¡Completado! {inserted_count} gastos importados.', 'complete': True, 'count': inserted_count})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            if os.path.exists(filepath):
                os.remove(filepath)
            if os.path.exists(job_file):
                os.remove(job_file)

    return app.response_class(generate(), mimetype='text/event-stream')


def extract_text_from_pdf(filepath):
    """Extract text from PDF file"""
    text = ""
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def parse_expenses_with_ai(text):
    """Parse expenses from PDF text using AI - processes in chunks for better results"""
    try:
        # Extract only the consumption sections from the text
        # Look for lines that contain transaction data
        lines = text.split('\n')

        # Find consumption sections
        consumption_lines = []
        in_consumption_section = False

        for line in lines:
            # Start capturing when we see "Consumos Clara Mesaglio"
            if 'Consumos' in line and ('Clara' in line or 'CLARA' in line):
                in_consumption_section = True
                continue

            # Stop at certain sections
            if any(keyword in line for keyword in ['TOTAL CONSUMOS', 'Impuestos', 'Legales y avisos', 'SALDO ACTUAL']):
                in_consumption_section = False
                continue

            # Capture transaction lines (skip BONIF lines)
            if in_consumption_section and line.strip():
                # Lines with dates typically start with day-month-year format
                # Skip bonus/discount lines
                if re.match(r'^\d{2}-[A-Za-z]{3}-\d{2}', line) and 'BONIF' not in line:
                    consumption_lines.append(line.strip())

        print(f"Found {len(consumption_lines)} transaction lines in PDF")

        # Process in chunks to avoid AI response limits
        chunk_size = 15  # Process 15 transactions at a time
        all_expenses = []

        for i in range(0, len(consumption_lines), chunk_size):
            chunk = consumption_lines[i:i + chunk_size]
            transactions_text = '\n'.join(chunk)

            print(f"Processing chunk {i//chunk_size + 1} of {(len(consumption_lines)-1)//chunk_size + 1}")

            prompt = f"""Sos un experto en análisis de resúmenes de tarjetas de crédito BBVA Argentina.

Analizá CADA LÍNEA del siguiente listado de transacciones y devolvé ÚNICAMENTE un JSON array.

Transacciones:
{transactions_text}

Formato de cada línea:
FECHA DESCRIPCIÓN [C.XX/YY si tiene cuotas] NRO_CUPON MONTO [DOLARES si aplica]

Para CADA transacción extraé:
- fecha: YYYY-MM-DD (año 2025 si dice "25", 2024 si dice "24")
- description: comercio/descripción
- amount: último número de la línea (convierte comas a puntos)
- currency: "USD" si contiene "USD", sino "ARS"
- installment_number: "X/Y" desde "C.XX/YY", null si no tiene
- category: Alimentación, Transporte, Salud, Entretenimiento, Servicios, Educación, Ropa, Otros
- payment_method: "Tarjeta de Crédito"

Devolvé SOLO el JSON array:
[{{"date":"2025-12-04","description":"AUTOPISTAS DEL S","amount":4334.38,"currency":"ARS","category":"Transporte","payment_method":"Tarjeta de Crédito","installment_number":null}}]
"""

            try:
                response = ollama.chat(
                    model='llama3.2',
                    messages=[
                        {'role': 'system', 'content': 'Devolvés SOLO JSON válido sin texto adicional.'},
                        {'role': 'user', 'content': prompt}
                    ],
                    options={
                        'num_predict': 3000,
                        'temperature': 0.1
                    }
                )

                ai_response = response['message']['content'].strip()

                # Remove markdown code blocks if present
                ai_response = re.sub(r'```json\s*', '', ai_response)
                ai_response = re.sub(r'```\s*', '', ai_response)
                ai_response = ai_response.strip()

                # Parse JSON
                chunk_expenses = json.loads(ai_response)

                # Validate and add to all_expenses
                for expense in chunk_expenses:
                    required_keys = ['date', 'description', 'amount', 'category', 'payment_method', 'currency']
                    if all(key in expense for key in required_keys):
                        expense['amount'] = float(expense['amount'])
                        expense['currency'] = expense['currency'].upper()
                        if 'installment_number' not in expense:
                            expense['installment_number'] = None
                        all_expenses.append(expense)

                print(f"Chunk {i//chunk_size + 1}: Parsed {len(chunk_expenses)} expenses")

            except Exception as e:
                print(f"Error processing chunk {i//chunk_size + 1}: {e}")
                continue

        print(f"Total validated expenses: {len(all_expenses)}")
        return all_expenses

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from AI: {e}")
        print(f"AI Response: {ai_response}")
        return []
    except Exception as e:
        print(f"Error in parse_expenses_with_ai: {e}")
        import traceback
        traceback.print_exc()
        return []

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

@app.route('/delete_expenses_bulk', methods=['POST'])
@login_required
def delete_expenses_bulk():
    """Delete multiple expenses at once"""
    try:
        data = request.get_json()
        expense_ids = data.get('expense_ids', [])

        if not expense_ids:
            return jsonify({'success': False, 'error': 'No se proporcionaron IDs de gastos'}), 400

        conn = get_db()
        cursor = conn.cursor()

        # Delete all selected expenses (only those belonging to the user)
        placeholders = ','.join('?' * len(expense_ids))
        query = f'DELETE FROM expenses WHERE id IN ({placeholders}) AND user_id = ?'
        cursor.execute(query, (*expense_ids, session['user_id']))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'{deleted_count} gasto(s) eliminado(s) correctamente'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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
    category_icon = request.form.get('category_icon', '').strip()

    if not category_name:
        flash('El nombre de la categoría es requerido', 'danger')
        return redirect(url_for('expenses'))

    # If no icon provided, use AI to suggest one
    if not category_icon:
        try:
            prompt = f"""Para la categoría de gastos llamada "{category_name}", sugiere UN SOLO emoji que sea representativo y apropiado.

Ejemplos:
- "Viaje" → ✈️
- "Mascotas" → 🐶
- "Gimnasio" → 💪
- "Café" → ☕
- "Libros" → 📚
- "Tecnología" → 💻

Respondé ÚNICAMENTE con el emoji, sin texto adicional."""

            response = ollama.chat(
                model='llama3.2',
                messages=[
                    {'role': 'system', 'content': 'Eres un asistente que sugiere emojis apropiados para categorías de gastos. Respondes SOLO con un emoji, nada más.'},
                    {'role': 'user', 'content': prompt}
                ],
                options={
                    'temperature': 0.3,
                    'num_predict': 10
                }
            )

            suggested_icon = response['message']['content'].strip()
            # Take only the first emoji if AI returned multiple characters
            category_icon = suggested_icon[:2] if suggested_icon else '📦'
        except Exception as e:
            print(f"Error suggesting icon with AI: {e}")
            category_icon = '📦'  # Fallback to default icon

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            'INSERT INTO custom_categories (user_id, name, icon) VALUES (?, ?, ?)',
            (session['user_id'], category_name, category_icon)
        )
        conn.commit()
        flash(f'Categoría "{category_name}" {category_icon} agregada exitosamente', 'success')
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
        download_name=f'AurefiQ_{year}_{month:02d}.csv'
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
