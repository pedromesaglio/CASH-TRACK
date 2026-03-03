"""
WSGI Entry Point para Cash Track
Este archivo es el punto de entrada para servidores WSGI como Gunicorn
"""

import os
from app import app

# Configurar el entorno si no está definido
if 'FLASK_ENV' not in os.environ:
    os.environ['FLASK_ENV'] = os.getenv('FLASK_ENV', 'production')

# Este es el objeto que Gunicorn va a usar
application = app

if __name__ == "__main__":
    # Si se ejecuta directamente, usar el servidor de desarrollo
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
