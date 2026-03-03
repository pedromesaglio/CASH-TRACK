"""
Configuración de Gunicorn para Cash Track
Para producción, ajusta los valores según tu servidor
"""

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
backlog = 2048

# Worker processes
# Regla general: (2 x $num_cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000  # Reciclar workers cada 1000 requests
max_requests_jitter = 50  # Variación aleatoria para evitar todos a la vez

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "cashtrack"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# En desarrollo
if os.getenv('FLASK_ENV') == 'development':
    reload = True
    workers = 2
    loglevel = "debug"
