# 🚂 Guía de Despliegue en Railway.app

Esta guía te llevará paso a paso para deployar Cash Track en Railway.app de forma gratuita.

## 📋 Pre-requisitos

- [x] Cuenta de GitHub con el repositorio de Cash Track
- [x] Archivos de configuración creados:
  - `Procfile` ✅
  - `railway.json` ✅
  - `requirements.txt` ✅
  - `.env.example` ✅
  - `database.py` actualizado ✅

## 🚀 Pasos para el Despliegue

### 1. Crear Cuenta en Railway

1. Ve a https://railway.app
2. Click en "Login" o "Start a New Project"
3. Elige "Login with GitHub"
4. Autoriza Railway a acceder a tu cuenta de GitHub

### 2. Crear Nuevo Proyecto

1. Una vez logueado, click en "New Project"
2. Selecciona "Deploy from GitHub repo"
3. Busca y selecciona tu repositorio: `CASH-TRACK` o `cash-track`
4. Railway comenzará a detectar tu proyecto

### 3. Agregar Base de Datos PostgreSQL

1. En tu proyecto, verás el servicio web que se está creando
2. Click en el botón "+ New" (arriba a la derecha)
3. Selecciona "Database"
4. Elige "Add PostgreSQL"
5. Railway creará automáticamente:
   - Una instancia de PostgreSQL
   - La variable de entorno `DATABASE_URL`
   - Conexión automática entre tu app y la base de datos

### 4. Configurar Variables de Entorno

1. Click en el servicio web (no en la base de datos)
2. Ve a la pestaña "Variables"
3. Agrega las siguientes variables manualmente:

```bash
SECRET_KEY=<genera-una-clave-segura-aquí>
FLASK_ENV=production
```

**Para generar una SECRET_KEY segura:**
```python
import secrets
print(secrets.token_hex(32))
```

**Variables que Railway crea automáticamente:**
- `DATABASE_URL` - Conexión a PostgreSQL (no la modifiques)
- `PORT` - Puerto asignado por Railway (no la modifiques)

### 5. Verificar Configuración de Deploy

1. Ve a la pestaña "Settings" de tu servicio web
2. En "Build Command" debería detectar automáticamente:
   ```
   pip install -r requirements.txt
   ```
3. En "Start Command" debería detectar desde el Procfile:
   ```
   gunicorn wsgi:app
   ```

Si no se detectan automáticamente, agrégalas manualmente.

### 6. Deploy Inicial

1. Railway detectará el push más reciente de tu repositorio
2. Comenzará el build automáticamente
3. Puedes ver los logs en tiempo real en la pestaña "Deployments"
4. Espera a que aparezca "Success" ✅

### 7. Generar Dominio Público

1. En el servicio web, ve a "Settings"
2. Baja hasta la sección "Networking"
3. Click en "Generate Domain"
4. Railway te asignará un dominio como:
   ```
   https://cash-track-production.up.railway.app
   ```
5. Copia este dominio - es donde tu app estará disponible 24/7

### 8. Inicializar Base de Datos

Una vez que tu app esté deployada, necesitas crear las tablas:

**Opción A - Desde Railway CLI:**
```bash
# Instalar Railway CLI
npm i -g @railway/cli

# Login
railway login

# Conectar al proyecto
railway link

# Ejecutar script de inicialización
railway run python database.py
```

**Opción B - Desde la Web Console:**
1. En tu proyecto de Railway, click en el servicio PostgreSQL
2. Ve a "Data" → "Query"
3. O usa una herramienta como TablePlus/pgAdmin con las credenciales de `DATABASE_URL`

### 9. Verificar que Todo Funciona

1. Abre el dominio generado en tu navegador
2. Deberías ver la página de login de Cash Track
3. Inicia sesión con las credenciales por defecto:
   - Usuario: `admin`
   - Contraseña: `admin`
4. **IMPORTANTE:** Cambia la contraseña del admin inmediatamente

### 10. Configurar Redeploy Automático

Railway ya está configurado para:
- ✅ Redesplegar automáticamente cuando hagas push a la rama `main`
- ✅ Mantener las variables de entorno entre deploys
- ✅ Reiniciar el servicio si hay errores

## 🔧 Troubleshooting

### Error: "Application failed to respond"
- Verifica que el `Procfile` existe y tiene: `web: gunicorn wsgi:app`
- Verifica en los logs que Gunicorn se está iniciando correctamente

### Error: "Database connection failed"
- Asegúrate de que agregaste la base de datos PostgreSQL
- Verifica que `DATABASE_URL` existe en las variables de entorno
- Revisa que ambos servicios (web y database) estén en el mismo proyecto

### Error: "Module not found"
- Verifica que todas las dependencias están en `requirements.txt`
- Revisa los logs de build para ver qué módulo falta

### La app se reinicia constantemente
- Revisa los logs en la pestaña "Deployments"
- Puede ser un error en el código o en las variables de entorno

## 📊 Monitoreo

Railway proporciona:
- **Logs en tiempo real:** Pestaña "Deployments" → Ver logs
- **Métricas:** CPU, RAM, Network usage
- **Uptime:** Railway mantiene tu app corriendo 24/7

## 💰 Costos

Railway ofrece:
- **Plan Free:** $5 de crédito gratis al mes
- **Uso típico de Cash Track:** ~$2-3/mes (dentro del free tier)
- **PostgreSQL:** Incluida en el free tier (500MB de almacenamiento)

## 🔄 Actualizaciones

Para actualizar tu app:
1. Haz cambios en tu código local
2. Commit y push a GitHub:
   ```bash
   git add .
   git commit -m "Nueva funcionalidad"
   git push origin main
   ```
3. Railway automáticamente:
   - Detectará el push
   - Rebuildeará la app
   - Redesplegarará sin downtime

## 📝 Credenciales Importantes

**Guarda en un lugar seguro:**
- URL de la app: `https://tu-app.up.railway.app`
- DATABASE_URL (en Railway Variables)
- SECRET_KEY (en Railway Variables)
- Credenciales de admin de la app

## ✅ Checklist Final

- [ ] Cuenta de Railway creada
- [ ] Proyecto creado desde GitHub
- [ ] PostgreSQL agregado
- [ ] Variables de entorno configuradas (SECRET_KEY, FLASK_ENV)
- [ ] Build exitoso
- [ ] Dominio generado
- [ ] Base de datos inicializada
- [ ] Login funcionando
- [ ] Contraseña de admin cambiada
- [ ] Redeploy automático verificado

## 🎉 ¡Listo!

Tu aplicación Cash Track está ahora deployada y disponible 24/7 en:
```
https://tu-app.up.railway.app
```

Los usuarios pueden acceder desde cualquier dispositivo con internet.

---

**Documentación de Railway:** https://docs.railway.app
**Soporte:** https://railway.app/discord (Discord oficial)
