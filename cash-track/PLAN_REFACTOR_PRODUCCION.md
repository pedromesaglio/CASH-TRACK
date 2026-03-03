# Plan de Refactor para Producción - Cash Track

## Estado Actual
- Base de datos: SQLite → **PostgreSQL** (en migración)
- Servidor: Flask Development Server
- Configuración: Variables hardcodeadas
- Seguridad: SECRET_KEY básica
- Estructura: Monolítica (app.py con 2030 líneas)

---

## FASE 1: Preparación de Base de Datos ✅

### 1.1 Migración a PostgreSQL
- [x] Script de migración creado (migrate_to_postgres.py)
- [x] Configuración de .env
- [ ] **ACCIÓN REQUERIDA:** Ejecutar `./migrate.sh`
- [ ] Verificar datos migrados correctamente
- [ ] Eliminar dependencias de SQLite en producción

---

## FASE 2: Configuración y Seguridad 🔐

### 2.1 Variables de Entorno
**Prioridad: CRÍTICA**

Archivos a crear:
- `.env.production` (para producción, NO commitear)
- `.env.development` (para desarrollo local)

Variables críticas que DEBES cambiar:
```bash
# Seguridad
SECRET_KEY=<generar_clave_criptográfica_fuerte_64_caracteres>
FLASK_ENV=production
FLASK_DEBUG=False

# PostgreSQL Production
POSTGRES_HOST=<tu_host_postgres>
POSTGRES_PORT=5432
POSTGRES_DB=cashtrack_prod
POSTGRES_USER=<usuario_seguro>
POSTGRES_PASSWORD=<contraseña_fuerte>

# APIs (si usas)
BINANCE_API_KEY=<opcional>
OLLAMA_HOST=<host_ollama_si_externo>
```

### 2.2 Secrets Management
- Usar variables de entorno para todos los secretos
- Cambiar `app.secret_key` hardcodeado (línea 19 de app.py)
- Generar SECRET_KEY criptográficamente segura:
  ```python
  import secrets
  print(secrets.token_hex(32))
  ```

### 2.3 Configuración de Seguridad
Agregar en app.py:
```python
# Security headers
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# Session configuration
app.config['SESSION_COOKIE_SECURE'] = True  # Solo HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hora
```

---

## FASE 3: Servidor de Producción 🚀

### 3.1 Gunicorn (WSGI Server)
**Reemplaza Flask development server**

Instalar:
```bash
pip install gunicorn psycopg2-binary python-dotenv
```

Crear `wsgi.py`:
```python
from app import app
import os

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
```

Comando para correr:
```bash
gunicorn --workers 4 --bind 0.0.0.0:8000 wsgi:app
```

### 3.2 Configuración de Gunicorn
Crear `gunicorn_config.py`:
```python
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "/var/log/cashtrack/access.log"
errorlog = "/var/log/cashtrack/error.log"
loglevel = "info"

# Process naming
proc_name = "cashtrack"

# Server mechanics
daemon = False
pidfile = "/var/run/cashtrack.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (si usas HTTPS directo, sino usa Nginx)
# keyfile = "/path/to/key.pem"
# certfile = "/path/to/cert.pem"
```

### 3.3 Nginx como Reverse Proxy
Crear `/etc/nginx/sites-available/cashtrack`:
```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name tu-dominio.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/tu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tu-dominio.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Logs
    access_log /var/log/nginx/cashtrack_access.log;
    error_log /var/log/nginx/cashtrack_error.log;

    # Max upload size (para PDFs)
    client_max_body_size 16M;

    # Static files
    location /static {
        alias /home/pedro/cashtrack/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Uploads
    location /uploads {
        alias /home/pedro/cashtrack/uploads;
        internal;  # Solo acceso interno
    }

    # Proxy to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;
    }
}
```

---

## FASE 4: Refactorización de Código 🏗️

### 4.1 Estructura Modular Recomendada
```
cash-track/
├── app/
│   ├── __init__.py           # App factory
│   ├── config.py             # Configuraciones
│   ├── models.py             # Modelos (o separados)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py          # Login, register, logout
│   │   ├── expenses.py      # Gestión de gastos
│   │   ├── income.py        # Gestión de ingresos
│   │   ├── investments.py   # Inversiones
│   │   ├── binance.py       # Integración Binance
│   │   ├── admin.py         # Panel admin
│   │   └── ai.py            # Endpoints AI
│   ├── services/
│   │   ├── __init__.py
│   │   ├── database.py      # Gestión DB
│   │   ├── pdf_processor.py # Procesamiento PDFs
│   │   ├── binance_api.py   # Cliente Binance
│   │   ├── price_api.py     # APIs de precios
│   │   └── ai_service.py    # Servicios de IA
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── decorators.py    # login_required, admin_required
│   │   ├── validators.py    # Validaciones
│   │   └── formatters.py    # Formateo de números
│   ├── static/
│   ├── templates/
│   └── migrations/          # Migraciones de DB
├── tests/                    # Tests unitarios
├── wsgi.py                  # Entry point WSGI
├── gunicorn_config.py
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
└── README.md
```

### 4.2 Separar Responsabilidades
**Problemas actuales en app.py:**
- 2030 líneas en un solo archivo
- Lógica de negocio mezclada con rutas
- Queries SQL directas en controladores
- Sin tests

**Patrón a implementar: Blueprint + Service Layer**

Ejemplo de refactor para expenses:

`app/routes/expenses.py`:
```python
from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.services.expense_service import ExpenseService
from app.utils.decorators import login_required

expenses_bp = Blueprint('expenses', __name__)
expense_service = ExpenseService()

@expenses_bp.route('/expenses', methods=['GET', 'POST'])
@login_required
def expenses():
    if request.method == 'POST':
        result = expense_service.create_expense(
            user_id=session['user_id'],
            data=request.form
        )
        if result.success:
            flash('Gasto agregado exitosamente', 'success')
        else:
            flash(result.error, 'danger')
        return redirect(url_for('expenses.expenses'))

    # GET logic
    expenses_data = expense_service.get_user_expenses(
        user_id=session['user_id'],
        year=request.args.get('year'),
        month=request.args.get('month')
    )

    return render_template('expenses.html', **expenses_data)
```

`app/services/expense_service.py`:
```python
from app.services.database import get_db
from typing import Dict, List, Optional

class ExpenseService:
    def create_expense(self, user_id: int, data: Dict) -> Result:
        """Create a new expense"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            # Validation
            if not self._validate_expense(data):
                return Result(success=False, error="Datos inválidos")

            # Insert
            cursor.execute('''
                INSERT INTO expenses (user_id, date, category, description, payment_method, amount, currency)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (user_id, data['date'], data['category'], ...))

            conn.commit()
            return Result(success=True)
        except Exception as e:
            return Result(success=False, error=str(e))
        finally:
            conn.close()

    def get_user_expenses(self, user_id: int, year: Optional[int], month: Optional[int]) -> Dict:
        """Get expenses with filtering"""
        # Business logic here
        pass
```

### 4.3 Migrations (Alembic)
Instalar:
```bash
pip install alembic
```

Inicializar:
```bash
alembic init migrations
```

Configurar `alembic.ini` y crear migraciones para cambios futuros.

---

## FASE 5: Dependencias y Requirements 📦

### 5.1 Archivo requirements.txt actualizado
```txt
Flask==3.0.0
psycopg2-binary==2.9.9
python-dotenv==1.0.0
Werkzeug==3.0.1
gunicorn==21.2.0

# APIs
requests==2.31.0
python-binance==1.0.19

# PDF processing
pdfplumber==0.10.3

# AI (Ollama)
ollama==0.1.6

# Security
cryptography==41.0.7

# Optional - Task Queue
# celery==5.3.4
# redis==5.0.1
```

### 5.2 Requirements de desarrollo
`requirements-dev.txt`:
```txt
pytest==7.4.3
pytest-cov==4.1.0
pytest-flask==1.3.0
black==23.12.1
flake8==6.1.0
mypy==1.7.1
```

---

## FASE 6: Docker y Containerización 🐳

### 6.1 Dockerfile
```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run gunicorn
CMD ["gunicorn", "--config", "gunicorn_config.py", "wsgi:app"]
```

### 6.2 docker-compose.yml
```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: cashtrack
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      DB_TYPE: postgresql
      POSTGRES_HOST: db
      POSTGRES_PORT: 5432
      POSTGRES_DB: cashtrack
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      SECRET_KEY: ${SECRET_KEY}
    volumes:
      - ./uploads:/app/uploads
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./static:/usr/share/nginx/html/static:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
```

---

## FASE 7: Monitoreo y Logs 📊

### 7.1 Logging estructurado
Agregar en `app/__init__.py`:
```python
import logging
from logging.handlers import RotatingFileHandler
import os

def configure_logging(app):
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')

        file_handler = RotatingFileHandler(
            'logs/cashtrack.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Cash Track startup')
```

### 7.2 Health Check endpoint
```python
@app.route('/health')
def health_check():
    """Health check endpoint para monitoreo"""
    try:
        # Check database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        conn.close()

        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500
```

---

## FASE 8: Despliegue en Plataformas Cloud ☁️

### Opción A: Render.com (Recomendada - Gratis)

**1. Preparar archivos:**
- `render.yaml`:
```yaml
services:
  - type: web
    name: cashtrack
    env: python
    region: oregon
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn wsgi:app
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: SECRET_KEY
        generateValue: true
      - key: DB_TYPE
        value: postgresql
      - key: POSTGRES_HOST
        fromDatabase:
          name: cashtrack-db
          property: host
      - key: POSTGRES_PORT
        fromDatabase:
          name: cashtrack-db
          property: port
      - key: POSTGRES_DB
        fromDatabase:
          name: cashtrack-db
          property: database
      - key: POSTGRES_USER
        fromDatabase:
          name: cashtrack-db
          property: user
      - key: POSTGRES_PASSWORD
        fromDatabase:
          name: cashtrack-db
          property: password

databases:
  - name: cashtrack-db
    plan: free
    databaseName: cashtrack
    user: cashtrack
```

**2. Deploy:**
1. Pushear código a GitHub
2. Conectar repo en Render.com
3. Render detecta `render.yaml` y crea servicios automáticamente
4. Esperar build y deploy

### Opción B: Railway.app

**1. Crear `railway.json`:**
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn wsgi:app",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**2. Deploy:**
```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

### Opción C: VPS (DigitalOcean, AWS EC2, Linode)

**Setup completo:**
```bash
# 1. Actualizar sistema
sudo apt update && sudo apt upgrade -y

# 2. Instalar dependencias
sudo apt install python3-pip python3-venv nginx postgresql postgresql-contrib -y

# 3. Crear usuario y directorio
sudo useradd -m -s /bin/bash cashtrack
sudo mkdir -p /var/www/cashtrack
sudo chown cashtrack:cashtrack /var/www/cashtrack

# 4. Clonar código
cd /var/www/cashtrack
sudo -u cashtrack git clone <tu-repo> .

# 5. Setup virtual env
sudo -u cashtrack python3 -m venv venv
sudo -u cashtrack venv/bin/pip install -r requirements.txt

# 6. Setup PostgreSQL
sudo -u postgres createdb cashtrack
sudo -u postgres createuser cashtrack
sudo -u postgres psql -c "ALTER USER cashtrack WITH PASSWORD 'tu_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE cashtrack TO cashtrack;"

# 7. Configurar systemd service
sudo nano /etc/systemd/system/cashtrack.service
```

`/etc/systemd/system/cashtrack.service`:
```ini
[Unit]
Description=Cash Track Application
After=network.target postgresql.service

[Service]
User=cashtrack
Group=cashtrack
WorkingDirectory=/var/www/cashtrack
Environment="PATH=/var/www/cashtrack/venv/bin"
ExecStart=/var/www/cashtrack/venv/bin/gunicorn --config gunicorn_config.py wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# 8. Iniciar servicio
sudo systemctl daemon-reload
sudo systemctl start cashtrack
sudo systemctl enable cashtrack

# 9. Configurar Nginx
sudo cp nginx_config /etc/nginx/sites-available/cashtrack
sudo ln -s /etc/nginx/sites-available/cashtrack /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# 10. SSL con Let's Encrypt
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d tu-dominio.com
```

---

## FASE 9: Performance y Optimización ⚡

### 9.1 Caching con Redis
```python
from flask_caching import Cache

cache = Cache(app, config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': os.getenv('REDIS_URL', 'redis://localhost:6379/0')
})

@app.route('/investments')
@cache.cached(timeout=300)  # 5 minutos
def investments():
    # ...
```

### 9.2 Database Connection Pooling
```python
from psycopg2 import pool

db_pool = pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    host=POSTGRES_CONFIG['host'],
    database=POSTGRES_CONFIG['database'],
    user=POSTGRES_CONFIG['user'],
    password=POSTGRES_CONFIG['password']
)

def get_db():
    return db_pool.getconn()

def return_db(conn):
    db_pool.putconn(conn)
```

### 9.3 Optimización de Queries
- Agregar índices en tablas:
```sql
CREATE INDEX idx_expenses_user_date ON expenses(user_id, date);
CREATE INDEX idx_expenses_category ON expenses(category);
CREATE INDEX idx_income_user_date ON income(user_id, date);
```

### 9.4 Compresión de Respuestas
```python
from flask_compress import Compress

Compress(app)
```

---

## FASE 10: Backup y Recuperación 💾

### 10.1 Script de Backup Automático
`backup_db.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/cashtrack"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/cashtrack_$DATE.sql.gz"

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
PGPASSWORD=$POSTGRES_PASSWORD pg_dump \
  -h localhost \
  -U $POSTGRES_USER \
  -d cashtrack \
  | gzip > $BACKUP_FILE

# Mantener solo últimos 7 días
find $BACKUP_DIR -name "cashtrack_*.sql.gz" -mtime +7 -delete

echo "Backup completado: $BACKUP_FILE"
```

### 10.2 Cron Job
```bash
# Backup diario a las 2 AM
0 2 * * * /var/www/cashtrack/backup_db.sh
```

---

## FASE 11: Testing 🧪

### 11.1 Setup de Tests
`tests/conftest.py`:
```python
import pytest
from app import create_app
from app.services.database import init_db

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        init_db()
        yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def authenticated_client(client):
    # Login logic
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    return client
```

### 11.2 Tests de Ejemplo
`tests/test_expenses.py`:
```python
def test_create_expense(authenticated_client):
    response = authenticated_client.post('/expenses', data={
        'date': '2026-03-03',
        'category': 'Alimentación',
        'description': 'Test',
        'payment_method': 'Efectivo',
        'amount': 1000
    })
    assert response.status_code == 302  # Redirect

def test_get_expenses(authenticated_client):
    response = authenticated_client.get('/expenses')
    assert response.status_code == 200
    assert b'Gastos' in response.data
```

### 11.3 CI/CD con GitHub Actions
`.github/workflows/tests.yml`:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - run: pip install -r requirements.txt -r requirements-dev.txt
    - run: pytest tests/ -v --cov=app
```

---

## FASE 12: Documentación 📚

### 12.1 README.md completo
### 12.2 API Documentation (si expones endpoints)
### 12.3 User Guide
### 12.4 Deployment Guide

---

## CHECKLIST FINAL ANTES DE PRODUCCIÓN ✅

### Seguridad
- [ ] SECRET_KEY criptográficamente segura
- [ ] Todas las contraseñas en variables de entorno
- [ ] HTTPS habilitado
- [ ] Headers de seguridad configurados
- [ ] SQL Injection protection (usar parámetros en queries)
- [ ] XSS protection
- [ ] CSRF protection (Flask-WTF)
- [ ] Rate limiting (Flask-Limiter)

### Base de Datos
- [ ] PostgreSQL configurado
- [ ] Datos migrados correctamente
- [ ] Backups automáticos configurados
- [ ] Índices creados
- [ ] Connection pooling habilitado

### Servidor
- [ ] Gunicorn instalado y configurado
- [ ] Nginx como reverse proxy
- [ ] SSL/TLS configurado
- [ ] Logs configurados
- [ ] Systemd service creado

### Código
- [ ] DEBUG=False en producción
- [ ] Código refactorizado (opcional pero recomendado)
- [ ] Tests pasando
- [ ] Sin datos de prueba en producción
- [ ] .gitignore actualizado

### Monitoreo
- [ ] Health check endpoint
- [ ] Logging estructurado
- [ ] Alertas configuradas (opcional)
- [ ] Métricas (opcional)

### Performance
- [ ] Compresión habilitada
- [ ] Static files servidos eficientemente
- [ ] Caching implementado (opcional)
- [ ] Database queries optimizadas

---

## COMANDOS RÁPIDOS DE REFERENCIA

### Desarrollo local
```bash
# Activar virtualenv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Correr en desarrollo
python app.py
```

### Producción
```bash
# Correr con Gunicorn
gunicorn --config gunicorn_config.py wsgi:app

# Reiniciar servicio
sudo systemctl restart cashtrack

# Ver logs
sudo journalctl -u cashtrack -f

# Backup manual
./backup_db.sh
```

### Docker
```bash
# Build
docker-compose build

# Run
docker-compose up -d

# Logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## PRÓXIMOS PASOS INMEDIATOS

1. **AHORA:** Ejecutar `./migrate.sh` para migrar a PostgreSQL
2. **HOY:** Cambiar SECRET_KEY y configurar .env.production
3. **ESTA SEMANA:**
   - Instalar y configurar Gunicorn
   - Testear localmente con PostgreSQL
   - Elegir plataforma de deploy (Render recomendado)
4. **PRÓXIMA SEMANA:**
   - Deploy inicial
   - Configurar SSL
   - Implementar backups

---

## RECURSOS ÚTILES

- [Flask Production Best Practices](https://flask.palletsprojects.com/en/2.3.x/deploying/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [PostgreSQL Performance](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [Render.com Deployment](https://render.com/docs)
- [Let's Encrypt SSL](https://letsencrypt.org/getting-started/)

---

**Autor:** Claude Code Assistant
**Fecha:** 2026-03-03
**Versión:** 1.0
