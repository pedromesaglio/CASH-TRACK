"""
Main Blueprint - Dashboard/Index route
"""
from flask import Blueprint, render_template, request, session
from datetime import datetime
from database import get_db
from app.utils.decorators import login_required
from app.services.dollar_scraper import get_dollar_rate_with_fallback

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
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
            SELECT EXTRACT(YEAR FROM date)::text as year, TO_CHAR(date, 'MM') as month
            FROM (
                SELECT date FROM expenses WHERE user_id = %s
                UNION ALL
                SELECT date FROM income WHERE user_id = %s
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
        WHERE user_id = %s AND EXTRACT(YEAR FROM date)::text = %s AND TO_CHAR(date, 'MM') = %s
        AND (currency = 'ARS' OR currency IS NULL)
    ''', (user_id, str(year), f'{month:02d}'))
    total_ars_expenses = cursor.fetchone()['total']

    # Total USD expenses for the month
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) as total
        FROM expenses
        WHERE user_id = %s AND EXTRACT(YEAR FROM date)::text = %s AND TO_CHAR(date, 'MM') = %s
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
        WHERE user_id = %s AND EXTRACT(YEAR FROM date)::text = %s AND TO_CHAR(date, 'MM') = %s
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
        WHERE user_id = %s AND EXTRACT(YEAR FROM date)::text = %s AND TO_CHAR(date, 'MM') = %s
        AND (currency = 'ARS' OR currency IS NULL)
    ''', (user_id, str(prev_year), f'{prev_month:02d}'))
    prev_total_ars_expenses = cursor.fetchone()['total']

    # Previous month USD expenses
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) as total
        FROM expenses
        WHERE user_id = %s AND EXTRACT(YEAR FROM date)::text = %s AND TO_CHAR(date, 'MM') = %s
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
        WHERE user_id = %s AND EXTRACT(YEAR FROM date)::text = %s AND TO_CHAR(date, 'MM') = %s
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
        WHERE user_id = %s AND EXTRACT(YEAR FROM date)::text = %s AND TO_CHAR(date, 'MM') = %s
        GROUP BY category
        ORDER BY total DESC
    ''', (user_id, str(year), f'{month:02d}'))
    expenses_by_category = cursor.fetchall()

    # Get all expenses grouped by category for detailed view
    cursor.execute('''
        SELECT * FROM expenses
        WHERE user_id = %s AND EXTRACT(YEAR FROM date)::text = %s AND TO_CHAR(date, 'MM') = %s
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
        WHERE user_id = %s AND EXTRACT(YEAR FROM date)::text = %s AND TO_CHAR(date, 'MM') = %s
        ORDER BY date DESC, created_at DESC
        LIMIT 10
    ''', (user_id, str(year), f'{month:02d}'))
    recent_expenses = cursor.fetchall()

    # Recent income
    cursor.execute('''
        SELECT * FROM income
        WHERE user_id = %s AND EXTRACT(YEAR FROM date)::text = %s AND TO_CHAR(date, 'MM') = %s
        ORDER BY date DESC, created_at DESC
        LIMIT 10
    ''', (user_id, str(year), f'{month:02d}'))
    recent_income = cursor.fetchall()

    # Total investments
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) as total_invested,
               COALESCE(SUM(COALESCE(current_value, amount)), 0) as total_current
        FROM investments
        WHERE user_id = %s
    ''', (user_id,))
    investments_totals = cursor.fetchone()

    total_invested = investments_totals['total_invested']
    total_current = investments_totals['total_current']
    investment_profit = total_current - total_invested

    # Get last 6 months data for trend chart
    cursor.execute('''
        SELECT TO_CHAR(date, 'YYYY-MM') as month,
               SUM(amount) as total
        FROM expenses
        WHERE user_id = %s
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
    ''', (user_id,))
    monthly_expenses = cursor.fetchall()

    cursor.execute('''
        SELECT TO_CHAR(date, 'YYYY-MM') as month,
               SUM(amount) as total
        FROM income
        WHERE user_id = %s
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
