"""
Módulo para obtener precios en tiempo real de inversiones
Soporta criptomonedas y acciones
"""
import requests
from typing import Dict, Optional

class PriceAPI:
    """Clase para obtener precios de diferentes activos"""

    def __init__(self):
        self.coingecko_url = "https://api.coingecko.com/api/v3"
        self.binance_url = "https://api.binance.com/api/v3"

    def get_crypto_price_usd(self, symbol: str) -> Optional[float]:
        """
        Obtiene el precio de una criptomoneda en USD

        Args:
            symbol: Símbolo de la cripto (BTC, ETH, etc.)

        Returns:
            Precio en USD o None si hay error
        """
        try:
            # Mapeo de símbolos a IDs de CoinGecko
            crypto_map = {
                'BTC': 'bitcoin',
                'ETH': 'ethereum',
                'USDT': 'tether',
                'BNB': 'binancecoin',
                'ADA': 'cardano',
                'SOL': 'solana',
                'DOT': 'polkadot',
                'DOGE': 'dogecoin',
                'MATIC': 'matic-network',
                'UNI': 'uniswap'
            }

            symbol_upper = symbol.upper()
            if symbol_upper not in crypto_map:
                print(f"⚠️  Símbolo {symbol} no soportado")
                return None

            crypto_id = crypto_map[symbol_upper]

            # Llamada a CoinGecko API
            url = f"{self.coingecko_url}/simple/price"
            params = {
                'ids': crypto_id,
                'vs_currencies': 'usd'
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            price = data.get(crypto_id, {}).get('usd')

            if price:
                print(f"✅ {symbol_upper}: ${price:,.2f} USD")
                return float(price)

            return None

        except requests.RequestException as e:
            print(f"❌ Error obteniendo precio de {symbol}: {e}")
            return None
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            return None

    def get_stock_price_usd(self, symbol: str) -> Optional[float]:
        """
        Obtiene el precio de una acción en USD usando Yahoo Finance API alternativa

        Args:
            symbol: Símbolo de la acción (AAPL, GOOGL, etc.)

        Returns:
            Precio en USD o None si hay error
        """
        try:
            # Usamos una API pública alternativa de Yahoo Finance
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            params = {
                'interval': '1d',
                'range': '1d'
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Extraer precio actual
            result = data.get('chart', {}).get('result', [])
            if result:
                meta = result[0].get('meta', {})
                price = meta.get('regularMarketPrice')

                if price:
                    print(f"✅ {symbol}: ${price:,.2f} USD")
                    return float(price)

            return None

        except requests.RequestException as e:
            print(f"❌ Error obteniendo precio de {symbol}: {e}")
            return None
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            return None

    def convert_usd_to_ars(self, usd_amount: float, exchange_rate: float = 1200) -> float:
        """
        Convierte USD a ARS

        Args:
            usd_amount: Cantidad en USD
            exchange_rate: Tasa de cambio USD/ARS (default 1200)

        Returns:
            Cantidad en ARS
        """
        return usd_amount * exchange_rate

    def get_asset_price(self, asset_type: str, symbol: str, exchange_rate: float = 1200) -> Optional[float]:
        """
        Obtiene el precio de un activo y lo convierte a ARS

        Args:
            asset_type: Tipo de activo ('Criptomonedas' o 'Acciones')
            symbol: Símbolo del activo
            exchange_rate: Tasa USD/ARS

        Returns:
            Precio en ARS o None si hay error
        """
        price_usd = None

        if asset_type.lower() in ['criptomonedas', 'crypto', 'cripto']:
            price_usd = self.get_crypto_price_usd(symbol)
        elif asset_type.lower() in ['acciones', 'stocks', 'accion']:
            price_usd = self.get_stock_price_usd(symbol)
        else:
            print(f"⚠️  Tipo de activo '{asset_type}' no soportado para actualización automática")
            return None

        if price_usd:
            price_ars = self.convert_usd_to_ars(price_usd, exchange_rate)
            return price_ars

        return None


def get_exchange_rate_usd_ars() -> float:
    """
    Obtiene la tasa de cambio USD/ARS actual
    Si falla, retorna un valor por defecto

    Returns:
        Tasa de cambio USD/ARS
    """
    try:
        # API gratuita para obtener tasa de cambio
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()
        ars_rate = data.get('rates', {}).get('ARS')

        if ars_rate:
            # La API oficial suele dar el dólar oficial, multiplicamos por un factor
            # para aproximarnos al dólar blue/MEP
            blue_rate = ars_rate * 1.5  # Aproximación
            print(f"💱 Tasa USD/ARS: ${blue_rate:.2f}")
            return blue_rate

        return 1200  # Valor por defecto

    except Exception as e:
        print(f"⚠️  Error obteniendo tasa de cambio, usando valor por defecto: {e}")
        return 1200  # Valor por defecto


if __name__ == '__main__':
    # Pruebas
    print("🔍 Probando API de precios...\n")

    api = PriceAPI()

    print("=== CRIPTOMONEDAS ===")
    btc_price = api.get_crypto_price_usd('BTC')
    eth_price = api.get_crypto_price_usd('ETH')

    print("\n=== ACCIONES ===")
    aapl_price = api.get_stock_price_usd('AAPL')
    googl_price = api.get_stock_price_usd('GOOGL')

    print("\n=== TASA DE CAMBIO ===")
    exchange_rate = get_exchange_rate_usd_ars()

    if btc_price:
        btc_ars = api.convert_usd_to_ars(btc_price, exchange_rate)
        print(f"\n💰 1 BTC = ${btc_ars:,.2f} ARS")

    if aapl_price:
        aapl_ars = api.convert_usd_to_ars(aapl_price, exchange_rate)
        print(f"💰 1 AAPL = ${aapl_ars:,.2f} ARS")
