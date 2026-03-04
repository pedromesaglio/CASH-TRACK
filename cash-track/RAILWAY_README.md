# 🚂 Cash Track - Listo para Railway.app

## ✅ Archivos de Configuración Creados

Tu aplicación está **100% lista** para deployar en Railway. Se han creado los siguientes archivos:

### 1. **Procfile**
Define el comando de inicio para Railway:
```
web: gunicorn wsgi:app
```

### 2. **railway.json**
Configuración específica de Railway:
- Builder: NIXPACKS
- Start command: `gunicorn wsgi:app`
- Política de reinicio: ON_FAILURE
- Reintentos máximos: 10

### 3. **requirements.txt**
Todas las dependencias de Python necesarias:
- Flask 3.0.0
- Gunicorn 21.2.0
- psycopg2-binary 2.9.9
- python-dotenv 1.0.0
- requests, beautifulsoup4, PyPDF2, ollama

### 4. **.env.example**
Template de variables de entorno documentadas

### 5. **database.py (actualizado)**
Detecta automáticamente la variable `DATABASE_URL` de Railway y se conecta a PostgreSQL

### 6. **.gitignore (actualizado)**
Protege archivos sensibles y backups

### 7. **RAILWAY_DEPLOYMENT.md**
Guía paso a paso completa para el despliegue

## 🚀 Próximos Pasos

### Opción A: Deploy Rápido (Web Interface)

1. Ve a https://railway.app
2. Login con GitHub
3. "New Project" → "Deploy from GitHub repo"
4. Selecciona tu repositorio
5. Agrega PostgreSQL: "+ New" → "Database" → "PostgreSQL"
6. Configura variables de entorno:
   - `SECRET_KEY`: Genera una clave segura
   - `FLASK_ENV`: production
7. Generate Domain en Settings → Networking
8. Inicializa la BD ejecutando: `railway run python database.py`

### Opción B: Deploy con Railway CLI

```bash
# 1. Instalar Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Inicializar proyecto
railway init

# 4. Agregar PostgreSQL
railway add

# 5. Configurar variables
railway variables set SECRET_KEY=tu-clave-segura
railway variables set FLASK_ENV=production

# 6. Deploy
railway up

# 7. Inicializar BD
railway run python database.py

# 8. Generar dominio
railway domain
```

## 📋 Variables de Entorno Necesarias

### Variables que Railway crea automáticamente:
- `DATABASE_URL` - Conexión a PostgreSQL (cuando agregues la database)
- `PORT` - Puerto asignado por Railway

### Variables que debes agregar manualmente:
- `SECRET_KEY` - Clave secreta para Flask sessions
- `FLASK_ENV` - Debe ser "production"

### Para generar SECRET_KEY:
```python
import secrets
print(secrets.token_hex(32))
# Copia el resultado y úsalo como SECRET_KEY
```

## 🔒 Seguridad

- ✅ SECRET_KEY desde variables de entorno
- ✅ PostgreSQL con conexión segura
- ✅ HTTPS automático en Railway
- ✅ Headers de seguridad configurados
- ✅ Session cookies securizadas

## 📊 Después del Deploy

1. **Accede a tu app:** `https://tu-app.up.railway.app`
2. **Login inicial:**
   - Usuario: `admin`
   - Password: `admin`
3. **IMPORTANTE:** Cambia la contraseña del admin inmediatamente

## 🔄 Actualizaciones Automáticas

Railway está configurado para redesplegar automáticamente cuando hagas push a `main`:

```bash
git add .
git commit -m "Nueva funcionalidad"
git push origin main
```

Railway detectará el push y redespleará sin downtime.

## 💰 Costos

- **Free tier:** $5/mes de crédito gratis
- **Uso estimado:** $2-3/mes para esta app
- **PostgreSQL:** Incluida (500MB)

## 📚 Documentación

- **Deployment completo:** Ver `RAILWAY_DEPLOYMENT.md`
- **Production checklist:** Ver `PRODUCTION_CHECKLIST.md`
- **Variables de entorno:** Ver `.env.example`

## 🆘 Soporte

Si tienes problemas:
1. Revisa los logs en Railway dashboard
2. Consulta `RAILWAY_DEPLOYMENT.md` → sección Troubleshooting
3. Railway Discord: https://railway.app/discord
4. Documentación oficial: https://docs.railway.app

## ✅ Checklist Rápido

Antes de deployar, verifica:
- [ ] Código pusheado a GitHub
- [ ] Cuenta de Railway creada
- [ ] SECRET_KEY generada

Durante el deploy:
- [ ] Repositorio conectado
- [ ] PostgreSQL agregado
- [ ] Variables configuradas
- [ ] Build exitoso
- [ ] Dominio generado
- [ ] BD inicializada

Después del deploy:
- [ ] Login funciona
- [ ] Password de admin cambiada
- [ ] Todas las secciones funcionan

## 🎉 ¡Listo para Producción!

Tu aplicación Cash Track está completamente preparada para Railway.app.

**Siguiente paso:** Sigue la guía en `RAILWAY_DEPLOYMENT.md` para deployar.

---

Última actualización: 2026-03-04
