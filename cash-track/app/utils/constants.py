"""
Application constants
"""

# Categories and payment methods
CATEGORIES = [
    'Alimentación',
    'Transporte',
    'Salud',
    'Entretenimiento',
    'Servicios',
    'Educación',
    'Ropa',
    'Otros'
]

PAYMENT_METHODS = [
    'Efectivo',
    'Tarjeta de Débito',
    'Tarjeta de Crédito',
    'Transferencia',
    'Otros'
]

INVESTMENT_PLATFORMS = [
    'Binance',
    'Bull Market',
    'Invertir Online',
    'Kraken',
    'Coinbase',
    'Mercado Pago',
    'Ualá',
    'Brubank',
    'Otros'
]

# Default category icons
DEFAULT_CATEGORY_ICONS = {
    'Alimentación': '🍽️',
    'Transporte': '🚗',
    'Salud': '⚕️',
    'Entretenimiento': '🎉',
    'Servicios': '🏠',
    'Educación': '📚',
    'Ropa': '👕',
    'Otros': '📦'
}

# Upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
