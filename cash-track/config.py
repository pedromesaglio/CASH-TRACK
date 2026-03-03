"""
Configuración de la aplicación Cash Track
Diferentes configuraciones para desarrollo, testing y producción
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuración base"""
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Database
    DB_TYPE = os.getenv('DB_TYPE', 'sqlite')
    SQLITE_DATABASE = os.getenv('SQLITE_DATABASE', 'cashtrack.db')

    # PostgreSQL
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'cashtrack')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')

    # Upload configuration
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    ALLOWED_EXTENSIONS = {'pdf'}

    # Session configuration
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    SESSION_COOKIE_SECURE = False  # True en producción con HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Categories and constants
    CATEGORIES = ['Alimentación', 'Transporte', 'Salud', 'Entretenimiento',
                 'Servicios', 'Educación', 'Ropa', 'Otros']
    PAYMENT_METHODS = ['Efectivo', 'Tarjeta de Débito', 'Tarjeta de Crédito',
                      'Transferencia', 'Otros']
    INVESTMENT_PLATFORMS = ['Binance', 'Bull Market', 'Invertir Online', 'Kraken',
                          'Coinbase', 'Mercado Pago', 'Ualá', 'Brubank', 'Otros']


class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True
    FLASK_ENV = 'development'
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False
    FLASK_ENV = 'production'
    SESSION_COOKIE_SECURE = True  # Requiere HTTPS

    # Validar que SECRET_KEY no sea la default
    def __init__(self):
        if self.SECRET_KEY == 'dev-secret-key-change-in-production':
            raise ValueError(
                "❌ SECURITY ERROR: Debes configurar una SECRET_KEY segura en producción!\n"
                "Genera una con: python3 -c 'import secrets; print(secrets.token_hex(32))'\n"
                "Y agrégala al archivo .env como SECRET_KEY=tu_clave_generada"
            )


class TestingConfig(Config):
    """Configuración para testing"""
    TESTING = True
    DEBUG = True
    DB_TYPE = 'sqlite'
    SQLITE_DATABASE = ':memory:'  # Base de datos en memoria para tests


# Diccionario de configuraciones
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    """Obtiene la configuración según el entorno"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    return config.get(config_name, config['default'])
