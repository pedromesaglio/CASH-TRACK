"""
Módulo para integración con Binance API
Permite obtener precios en tiempo real y balances de wallet
"""
from binance.client import Client
from binance.exceptions import BinanceAPIException
from typing import Dict, Optional, List
from database import get_db

class BinanceIntegration:
    """Clase para integración con Binance API"""

    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = False):
        """
        Inicializa el cliente de Binance

        Args:
            api_key: API Key de Binance
            api_secret: API Secret de Binance
            testnet: Si es True, usa Binance Testnet
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.client = None

        if api_key and api_secret:
            try:
                if testnet:
                    self.client = Client(api_key, api_secret, testnet=True)
                    self.client.API_URL = 'https://testnet.binance.vision/api'
                else:
                    self.client = Client(api_key, api_secret)
                print("✅ Conexión establecida con Binance API")
            except BinanceAPIException as e:
                print(f"❌ Error conectando con Binance: {e}")
                self.client = None

    @staticmethod
    def get_user_credentials(user_id: int) -> Optional[Dict]:
        """
        Obtiene las credenciales de Binance del usuario desde la base de datos

        Args:
            user_id: ID del usuario

        Returns:
            Diccionario con las credenciales o None
        """
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT api_key, api_secret, is_testnet
            FROM binance_credentials
            WHERE user_id = ?
        ''', (user_id,))

        creds = cursor.fetchone()
        conn.close()

        if creds:
            return {
                'api_key': creds['api_key'],
                'api_secret': creds['api_secret'],
                'is_testnet': bool(creds['is_testnet'])
            }
        return None

    @staticmethod
    def save_credentials(user_id: int, api_key: str, api_secret: str, is_testnet: bool = False) -> bool:
        """
        Guarda las credenciales de Binance en la base de datos

        Args:
            user_id: ID del usuario
            api_key: API Key de Binance
            api_secret: API Secret de Binance
            is_testnet: Si es True, las credenciales son para testnet

        Returns:
            True si se guardó exitosamente
        """
        try:
            conn = get_db()
            cursor = conn.cursor()

            # Verificar si ya existen credenciales
            cursor.execute('SELECT id FROM binance_credentials WHERE user_id = ?', (user_id,))
            existing = cursor.fetchone()

            if existing:
                # Actualizar credenciales existentes
                cursor.execute('''
                    UPDATE binance_credentials
                    SET api_key = ?, api_secret = ?, is_testnet = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (api_key, api_secret, is_testnet, user_id))
            else:
                # Insertar nuevas credenciales
                cursor.execute('''
                    INSERT INTO binance_credentials (user_id, api_key, api_secret, is_testnet)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, api_key, api_secret, is_testnet))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"❌ Error guardando credenciales: {e}")
            return False

    @staticmethod
    def delete_credentials(user_id: int) -> bool:
        """
        Elimina las credenciales de Binance del usuario

        Args:
            user_id: ID del usuario

        Returns:
            True si se eliminó exitosamente
        """
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM binance_credentials WHERE user_id = ?', (user_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Error eliminando credenciales: {e}")
            return False

    def get_account_balance(self) -> Optional[List[Dict]]:
        """
        Obtiene los balances de la cuenta de Binance

        Returns:
            Lista de diccionarios con balances de cada activo o None si hay error
        """
        if not self.client:
            print("⚠️  Cliente de Binance no inicializado")
            return None

        try:
            account = self.client.get_account()
            balances = []

            for balance in account['balances']:
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked

                # Solo incluir activos con balance mayor a 0
                if total > 0:
                    balances.append({
                        'asset': balance['asset'],
                        'free': free,
                        'locked': locked,
                        'total': total
                    })

            return balances

        except BinanceAPIException as e:
            print(f"❌ Error obteniendo balances: {e}")
            return None
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            return None

    def get_crypto_price(self, symbol: str) -> Optional[float]:
        """
        Obtiene el precio actual de una criptomoneda en USDT

        Args:
            symbol: Símbolo de la cripto (BTC, ETH, etc.)

        Returns:
            Precio en USDT o None si hay error
        """
        if not self.client:
            print("⚠️  Cliente de Binance no inicializado")
            return None

        try:
            # Binance usa pares de trading, por ejemplo BTCUSDT
            symbol_upper = symbol.upper()

            # Agregar USDT si no lo tiene
            if not symbol_upper.endswith('USDT'):
                trading_pair = f"{symbol_upper}USDT"
            else:
                trading_pair = symbol_upper

            ticker = self.client.get_symbol_ticker(symbol=trading_pair)
            price = float(ticker['price'])

            print(f"✅ {symbol_upper}: ${price:,.2f} USDT")
            return price

        except BinanceAPIException as e:
            print(f"❌ Error obteniendo precio de {symbol}: {e}")
            return None
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            return None

    def get_all_prices(self) -> Optional[Dict[str, float]]:
        """
        Obtiene todos los precios de Binance

        Returns:
            Diccionario con símbolos y precios o None si hay error
        """
        if not self.client:
            print("⚠️  Cliente de Binance no inicializado")
            return None

        try:
            tickers = self.client.get_all_tickers()
            prices = {}

            for ticker in tickers:
                symbol = ticker['symbol']
                price = float(ticker['price'])
                prices[symbol] = price

            return prices

        except BinanceAPIException as e:
            print(f"❌ Error obteniendo precios: {e}")
            return None
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            return None

    def test_connection(self) -> bool:
        """
        Prueba la conexión con Binance API

        Returns:
            True si la conexión es exitosa
        """
        if not self.client:
            return False

        try:
            # Ping a la API
            self.client.ping()

            # Verificar tiempo del servidor
            server_time = self.client.get_server_time()
            print(f"✅ Conexión exitosa - Server time: {server_time['serverTime']}")

            # Intentar obtener info de la cuenta
            account = self.client.get_account()
            print(f"✅ Cuenta verificada - Permisos: {', '.join(account['permissions'])}")

            return True

        except BinanceAPIException as e:
            print(f"❌ Error en test de conexión: {e}")
            return False
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            return False


def get_binance_client_for_user(user_id: int) -> Optional[BinanceIntegration]:
    """
    Crea un cliente de Binance para un usuario específico

    Args:
        user_id: ID del usuario

    Returns:
        Instancia de BinanceIntegration o None si no hay credenciales
    """
    creds = BinanceIntegration.get_user_credentials(user_id)

    if not creds:
        return None

    return BinanceIntegration(
        api_key=creds['api_key'],
        api_secret=creds['api_secret'],
        testnet=creds['is_testnet']
    )


if __name__ == '__main__':
    # Pruebas básicas
    print("🔍 Probando módulo Binance API...\n")

    # Crear cliente sin credenciales (solo precios públicos)
    print("=== PRUEBA SIN CREDENCIALES ===")
    client = BinanceIntegration()

    if client.client:
        # Obtener algunos precios
        btc_price = client.get_crypto_price('BTC')
        eth_price = client.get_crypto_price('ETH')

        print("\n=== PRECIOS OBTENIDOS ===")
        if btc_price:
            print(f"BTC: ${btc_price:,.2f}")
        if eth_price:
            print(f"ETH: ${eth_price:,.2f}")
