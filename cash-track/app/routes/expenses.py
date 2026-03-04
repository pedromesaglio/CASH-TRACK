"""
Expenses Blueprint - Expense management and PDF processing
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from werkzeug.utils import secure_filename
from datetime import datetime
import csv
import io
import os
import uuid
import json
from database import get_db
from app.utils.decorators import login_required
from app.utils.constants import PAYMENT_METHODS
from app.services.category_service import get_all_categories, get_category_icons, get_custom_categories
from app.services.pdf_processor import process_pdf_expenses
import ollama

expenses_bp = Blueprint('expenses', __name__)


@expenses_bp.route('/expenses', methods=['GET', 'POST'])
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
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (session['user_id'], date, category, description, payment_method, amount, currency))
        conn.commit()
        conn.close()

        flash('Gasto agregado exitosamente', 'success')
        return redirect(url_for('expenses.expenses'))

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
            SELECT EXTRACT(YEAR FROM date)::text as year, TO_CHAR(date, 'MM') as month
            FROM expenses
            WHERE user_id = %s
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
        WHERE user_id = %s AND EXTRACT(YEAR FROM date)::text = %s AND TO_CHAR(date, 'MM') = %s
        ORDER BY date DESC, created_at DESC
    ''', (user_id, str(year), f'{month:02d}'))
    all_expenses = cursor.fetchall()

    # Get custom categories for management (before closing connection)
    custom_categories = get_custom_categories(session['user_id'])

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


@expenses_bp.route('/expenses/all')
@login_required
def expenses_all():
    """Show all expenses without date filter"""
    conn = get_db()
    cursor = conn.cursor()

    # Get ALL expenses for the user
    cursor.execute('''
        SELECT * FROM expenses
        WHERE user_id = %s
        ORDER BY date DESC, created_at DESC
        LIMIT 100
    ''', (session['user_id'],))
    all_expenses = cursor.fetchall()

    conn.close()

    all_categories = get_all_categories(session['user_id'])
    category_icons = get_category_icons(session['user_id'])
    custom_categories = get_custom_categories(session['user_id'])

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


@expenses_bp.route('/delete_expense/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    """Delete an expense"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM expenses WHERE id = %s AND user_id = %s',
                   (expense_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Gasto eliminado', 'success')
    return redirect(url_for('expenses.expenses'))


@expenses_bp.route('/delete_expenses_bulk', methods=['POST'])
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
        placeholders = ','.join('%s' * len(expense_ids))
        query = f'DELETE FROM expenses WHERE id IN ({placeholders}) AND user_id = %s'
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


@expenses_bp.route('/add_category', methods=['POST'])
@login_required
def add_category():
    """Add a custom category"""
    category_name = request.form.get('category_name', '').strip()
    category_icon = request.form.get('category_icon', '').strip()

    if not category_name:
        flash('El nombre de la categoría es requerido', 'danger')
        return redirect(url_for('expenses.expenses'))

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
            'INSERT INTO custom_categories (user_id, name, icon) VALUES (%s, %s, %s)',
            (session['user_id'], category_name, category_icon)
        )
        conn.commit()
        flash(f'Categoría "{category_name}" {category_icon} agregada exitosamente', 'success')
    except Exception as e:
        flash('Esta categoría ya existe', 'danger')
    finally:
        conn.close()

    return redirect(url_for('expenses.expenses'))


@expenses_bp.route('/delete_category/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    """Delete a custom category"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM custom_categories WHERE id = %s AND user_id = %s',
                   (category_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Categoría eliminada', 'success')
    return redirect(url_for('expenses.expenses'))


@expenses_bp.route('/export_csv')
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
        WHERE user_id = %s AND EXTRACT(YEAR FROM date)::text = %s AND TO_CHAR(date, 'MM') = %s
        ORDER BY date DESC
    ''', (session['user_id'], str(year), f'{month:02d}'))
    expenses_data = cursor.fetchall()

    # Get income
    cursor.execute('''
        SELECT date, source, amount
        FROM income
        WHERE user_id = %s AND EXTRACT(YEAR FROM date)::text = %s AND TO_CHAR(date, 'MM') = %s
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


@expenses_bp.route('/upload_expenses_pdf', methods=['POST'])
@login_required
def upload_expenses_pdf():
    """Upload PDF and return job ID for progress tracking"""
    if 'pdf_file' not in request.files:
        flash('No se seleccionó ningún archivo', 'danger')
        return redirect(url_for('expenses.expenses'))

    file = request.files['pdf_file']

    if file.filename == '':
        flash('No se seleccionó ningún archivo', 'danger')
        return redirect(url_for('expenses.expenses'))

    if file and file.filename.lower().endswith('.pdf'):
        try:
            from app.utils.constants import UPLOAD_FOLDER

            # Create upload folder if it doesn't exist
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)

            # Save the file temporarily
            job_id = str(uuid.uuid4())
            filename = f"{job_id}_{secure_filename(file.filename)}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            # Store job metadata in a file
            job_file = os.path.join(UPLOAD_FOLDER, f"{job_id}.json")
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
            return redirect(url_for('expenses.expenses'))
    else:
        flash('Por favor sube un archivo PDF válido', 'danger')
        return redirect(url_for('expenses.expenses'))


@expenses_bp.route('/process_pdf/<job_id>')
@login_required
def process_pdf_stream(job_id):
    """Stream processing progress"""
    from flask import current_app

    def generate():
        from app.utils.constants import UPLOAD_FOLDER

        # Load job data from file
        job_file = os.path.join(UPLOAD_FOLDER, f"{job_id}.json")

        if not os.path.exists(job_file):
            yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
            return

        with open(job_file, 'r') as f:
            job_data = json.load(f)

        filepath = job_data['filepath']
        user_id = job_data['user_id']

        try:
            # Process PDF with progress updates
            for progress_update in process_pdf_expenses(filepath, user_id):
                yield f"data: {json.dumps(progress_update)}\n\n"

            # Remove temporary files
            if os.path.exists(filepath):
                os.remove(filepath)
            if os.path.exists(job_file):
                os.remove(job_file)

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            if os.path.exists(filepath):
                os.remove(filepath)
            if os.path.exists(job_file):
                os.remove(job_file)

    return current_app.response_class(generate(), mimetype='text/event-stream')
