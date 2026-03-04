"""
Income Blueprint - Income management
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from database import get_db
from app.utils.decorators import login_required

income_bp = Blueprint('income', __name__)


@income_bp.route('/income', methods=['GET', 'POST'])
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
            VALUES (%s, %s, %s, %s)
        ''', (session['user_id'], date, source, amount))
        conn.commit()
        conn.close()

        flash('Ingreso agregado exitosamente', 'success')
        return redirect(url_for('income.income'))

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
            SELECT EXTRACT(YEAR FROM date)::text as year, TO_CHAR(date, 'MM') as month
            FROM income
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
        SELECT * FROM income
        WHERE user_id = %s AND EXTRACT(YEAR FROM date)::text = %s AND TO_CHAR(date, 'MM') = %s
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


@income_bp.route('/delete_income/<int:income_id>', methods=['POST'])
@login_required
def delete_income(income_id):
    """Delete an income"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM income WHERE id = %s AND user_id = %s',
                   (income_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Ingreso eliminado', 'success')
    return redirect(url_for('income.income'))
