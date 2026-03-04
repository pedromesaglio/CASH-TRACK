"""
Investments Blueprint - Investment management and price updates
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from database import get_db
from app.utils.decorators import login_required
from app.utils.constants import INVESTMENT_PLATFORMS
from app.services.binance_api import BinanceIntegration, get_binance_client_for_user
from app.services.price_api import PriceAPI, get_exchange_rate_usd_ars

investments_bp = Blueprint('investments', __name__)


@investments_bp.route('/investments', methods=['GET', 'POST'])
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
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (session['user_id'], date, inv_type, name, amount, current_value, notes))
        conn.commit()
        conn.close()

        flash('Inversión agregada exitosamente', 'success')
        return redirect(url_for('investments.investments'))

    # GET request - show form and list
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM investments
        WHERE user_id = %s
        ORDER BY date DESC, created_at DESC
    ''', (session['user_id'],))
    all_investments = cursor.fetchall()

    # Calculate total invested and current value
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) as total_invested,
               COALESCE(SUM(COALESCE(current_value, amount)), 0) as total_current
        FROM investments
        WHERE user_id = %s
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


@investments_bp.route('/delete_investment/<int:investment_id>', methods=['POST'])
@login_required
def delete_investment(investment_id):
    """Delete an investment"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM investments WHERE id = %s AND user_id = %s',
                   (investment_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Inversión eliminada', 'success')
    return redirect(url_for('investments.investments'))


@investments_bp.route('/update_investment_prices', methods=['POST'])
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
            WHERE user_id = %s AND symbol IS NOT NULL AND symbol != ''
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
                        SET current_value = %s
                        WHERE id = %s
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
                        SET current_value = %s
                        WHERE id = %s
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

        return redirect(url_for('investments.investments'))

    except Exception as e:
        flash(f'❌ Error actualizando precios: {str(e)}', 'danger')
        return redirect(url_for('investments.investments'))
