"""
Binance Integration Routes
Handles Binance API configuration, credentials management, and balance synchronization
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from database import get_db
from app.utils.decorators import login_required
from app.services.binance_api import BinanceIntegration, get_binance_client_for_user
from app.services.price_api import get_exchange_rate_usd_ars

binance_bp = Blueprint('binance', __name__, url_prefix='/binance')


@binance_bp.route('/config', methods=['GET'])
@login_required
def binance_config():
    """Binance configuration page"""
    creds = BinanceIntegration.get_user_credentials(session['user_id'])

    has_credentials = creds is not None
    is_testnet = creds.get('is_testnet', False) if creds else False

    return render_template('binance_config.html',
                          has_credentials=has_credentials,
                          is_testnet=is_testnet)


@binance_bp.route('/save-credentials', methods=['POST'])
@login_required
def save_binance_credentials():
    """Save Binance API credentials"""
    api_key = request.form.get('api_key', '').strip()
    api_secret = request.form.get('api_secret', '').strip()
    is_testnet = request.form.get('is_testnet') == '1'

    if not api_key or not api_secret:
        flash('API Key y API Secret son requeridos', 'danger')
        return redirect(url_for('binance.binance_config'))

    # Probar la conexión antes de guardar
    try:
        test_client = BinanceIntegration(api_key, api_secret, is_testnet)
        if not test_client.test_connection():
            flash('❌ No se pudo conectar con Binance. Verifica tus credenciales', 'danger')
            return redirect(url_for('binance.binance_config'))
    except Exception as e:
        flash(f'❌ Error probando conexión: {str(e)}', 'danger')
        return redirect(url_for('binance.binance_config'))

    # Guardar credenciales
    if BinanceIntegration.save_credentials(session['user_id'], api_key, api_secret, is_testnet):
        flash('✅ Credenciales de Binance guardadas exitosamente', 'success')
    else:
        flash('❌ Error guardando credenciales', 'danger')

    return redirect(url_for('binance.binance_config'))


@binance_bp.route('/delete-credentials', methods=['POST'])
@login_required
def delete_binance_credentials():
    """Delete Binance API credentials"""
    if BinanceIntegration.delete_credentials(session['user_id']):
        flash('✅ Credenciales eliminadas exitosamente', 'success')
    else:
        flash('❌ Error eliminando credenciales', 'danger')

    return redirect(url_for('binance.binance_config'))


@binance_bp.route('/test-connection')
@login_required
def test_binance_connection():
    """Test Binance API connection"""
    binance_client = get_binance_client_for_user(session['user_id'])

    if not binance_client:
        flash('❌ No tienes credenciales de Binance configuradas', 'warning')
        return redirect(url_for('binance.binance_config'))

    if binance_client.test_connection():
        flash('✅ Conexión con Binance exitosa', 'success')
    else:
        flash('❌ Error en la conexión con Binance', 'danger')

    return redirect(url_for('binance.binance_config'))


@binance_bp.route('/balances')
@login_required
def binance_balances():
    """View Binance account balances"""
    binance_client = get_binance_client_for_user(session['user_id'])

    if not binance_client:
        flash('❌ No tienes credenciales de Binance configuradas', 'warning')
        return redirect(url_for('binance.binance_config'))

    balances = binance_client.get_account_balance()

    if balances is None:
        flash('❌ Error obteniendo balances de Binance', 'danger')
        return redirect(url_for('binance.binance_config'))

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


@binance_bp.route('/sync-to-investments', methods=['POST'])
@login_required
def sync_binance_to_investments():
    """Sync Binance balances to investments"""
    binance_client = get_binance_client_for_user(session['user_id'])

    if not binance_client:
        flash('❌ No tienes credenciales de Binance configuradas', 'warning')
        return redirect(url_for('binance.binance_config'))

    balances = binance_client.get_account_balance()

    if balances is None:
        flash('❌ Error obteniendo balances de Binance', 'danger')
        return redirect(url_for('binance.binance_balances'))

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
            WHERE user_id = %s AND type = 'Binance' AND symbol = %s
        ''', (session['user_id'], symbol))

        existing = cursor.fetchone()

        if existing:
            # Actualizar inversión existente
            cursor.execute('''
                UPDATE investments
                SET amount = %s, current_value = %s, notes = %s, date = %s
                WHERE id = %s
            ''', (total_value_ars, total_value_ars,
                  f'Sincronizado desde Binance - {total_amount} {symbol}',
                  datetime.now().strftime('%Y-%m-%d'),
                  existing['id']))
            updated_count += 1
        else:
            # Crear nueva inversión
            cursor.execute('''
                INSERT INTO investments (user_id, date, type, name, amount, current_value, notes, symbol)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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
