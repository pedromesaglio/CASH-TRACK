# Guía Rápida de Deployment - Cash Track

## 🚀 Pasos para poner en producción

### 1. Migrar a PostgreSQL (SI AÚN NO LO HICISTE)

Ejecuta uno de estos scripts:

**Opción A - Script bash:**
```bash
cd cash-track
./migrate.sh
```

**Opción B - Script Python:**
```bash
# Primero, crea el usuario y la base de datos PostgreSQL:
sudo -u postgres psql -c "CREATE USER pedro WITH PASSWORD 'cashtrack2026';"
sudo -u postgres psql -c "ALTER USER pedro CREATEDB;"
sudo -u postgres psql -c "CREATE DATABASE cashtrack OWNER pedro;"

# Luego ejecuta el script:
python3 setup_postgres.py
```

### 2. Configurar variables de entorno para producción

Crea un archivo `.env.production`:
```bash
# PostgreSQL Production
DB_TYPE=postgresql
POSTGRES_HOST=<tu_host_postgres>
POSTGRES_PORT=5432
POSTGRES_DB=cashtrack
POSTGRES_USER=<usuario>
POSTGRES_PASSWORD=<contraseña_segura>

# Flask Configuration
SECRET_KEY=3d6db1dc9ac51cf2cdceb6f95693742574a4b213e924fd765f914a517af961e9
FLASK_ENV=production
FLASK_DEBUG=False
```

### 3. Testear localmente con Gunicorn

```bash
cd cash-track
gunicorn --config gunicorn_config.py wsgi:app
```

Abre http://localhost:8000 y verifica que todo funcione.

### 4. Deploy en Render.com (RECOMENDADO - Gratis)

1. **Pushea tu código a GitHub**
   ```bash
   git add .
   git commit -m "Ready for production"
   git push origin main
   ```

2. **Crea cuenta en Render.com**
   - Ve a https://render.com y crea una cuenta
   - Conecta tu repositorio de GitHub

3. **Crear base de datos PostgreSQL**
   - En Render, crea un nuevo "PostgreSQL" database (plan Free)
   - Anota las credenciales que te da Render

4. **Crear Web Service**
   - Crea un nuevo "Web Service"
   - Conecta tu repositorio
   - Configura:
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `gunicorn --config gunicorn_config.py wsgi:app`
     - **Environment:** Python 3

5. **Configurar variables de entorno en Render**
   En la sección "Environment", agrega:
   ```
   DB_TYPE=postgresql
   POSTGRES_HOST=<internal_host_de_render>
   POSTGRES_PORT=5432
   POSTGRES_DB=<db_name_de_render>
   POSTGRES_USER=<user_de_render>
   POSTGRES_PASSWORD=<password_de_render>
   SECRET_KEY=3d6db1dc9ac51cf2cdceb6f95693742574a4b213e924fd765f914a517af961e9
   FLASK_ENV=production
   ```

6. **Deploy!**
   - Click en "Create Web Service"
   - Render construirá y desplegará tu app automáticamente
   - Te dará una URL tipo: `https://cash-track.onrender.com`

### 5. Deploy en Railway.app (Alternativa fácil)

```bash
# Instalar CLI
npm install -g @railway/cli

# Login
railway login

# Iniciar proyecto
railway init

# Deploy
railway up
```

Railway creará automáticamente PostgreSQL y desplegará tu app.

### 6. Deploy en VPS (DigitalOcean, AWS, etc.)

Si prefieres un VPS, sigue la guía completa en `PLAN_REFACTOR_PRODUCCION.md` (Fase 8, Opción C).

## 📝 Checklist Pre-Producción

- [x] Migración a PostgreSQL completada
- [x] SECRET_KEY criptográficamente segura configurada
- [x] Gunicorn instalado
- [x] Variables de entorno configuradas
- [x] Headers de seguridad agregados
- [x] Session cookies configuradas correctamente
- [ ] Backup automático configurado (después del deploy)
- [ ] SSL/HTTPS habilitado (Render lo hace automático)

## 🔧 Comandos Útiles

### Desarrollo local
```bash
# Con Flask development server
python app.py

# Con Gunicorn (simulando producción)
gunicorn --config gunicorn_config.py wsgi:app
```

### Backup de base de datos
```bash
# PostgreSQL
pg_dump -h localhost -U pedro cashtrack > backup.sql

# Restaurar
psql -h localhost -U pedro cashtrack < backup.sql
```

### Ver logs en producción (Render)
- Ve al Dashboard de Render
- Click en tu servicio
- Tab "Logs"

## 🆘 Troubleshooting

### Error: "SECRET_KEY not configured"
- Verifica que el `.env` tenga `SECRET_KEY=...`
- En Render, verifica las Environment Variables

### Error: "Connection refused" PostgreSQL
- Verifica que PostgreSQL esté corriendo: `systemctl status postgresql`
- Verifica las credenciales en `.env`
- En Render, verifica que la base de datos esté "Available"

### Error 502 en Render
- Verifica los logs en Render Dashboard
- Asegúrate que el Start Command sea correcto
- Verifica que todas las dependencias estén en requirements.txt

## 📚 Más información

- Plan completo de refactor: `PLAN_REFACTOR_PRODUCCION.md`
- Documentación de Render: https://render.com/docs
- Documentación de Railway: https://docs.railway.app

---

**¿Listo para deploy?** Sigue los pasos 1-4 y tendrás tu app en producción en menos de 30 minutos! 🎉
