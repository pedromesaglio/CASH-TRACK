# Integración con Binance API

## 📋 Descripción

Cash Track ahora soporta integración directa con tu cuenta de Binance, permitiéndote:

- 🔑 Conectar tu cuenta de Binance mediante API Keys
- 💰 Ver tus balances en tiempo real
- 📈 Obtener precios actualizados de criptomonedas directamente desde Binance
- 🔄 Sincronizar automáticamente tus inversiones con tus balances de Binance
- 💱 Conversión automática de USD a ARS

## 🚀 Configuración Inicial

### Paso 1: Obtener API Keys de Binance

1. Inicia sesión en [Binance](https://www.binance.com)
2. Haz clic en tu icono de perfil (esquina superior derecha)
3. Selecciona **"API Management"** del menú
4. Haz clic en **"Create API"**
5. Completa el proceso de verificación (2FA)
6. **IMPORTANTE**: Configura los permisos de la API:
   - ✅ **Enable Reading** (Habilitar lectura) - REQUERIDO
   - ❌ **Enable Spot & Margin Trading** - NO MARCAR
   - ❌ **Enable Withdrawals** - NO MARCAR

7. Copia y guarda en un lugar seguro:
   - API Key
   - API Secret

### Paso 2: Configurar en Cash Track

1. Accede a la aplicación Cash Track
2. Haz clic en **"🟡 Binance"** en el menú de navegación
3. Ingresa tu **API Key** y **API Secret**
4. (Opcional) Marca "Usar Binance Testnet" si estás usando credenciales de prueba
5. Haz clic en **"💾 Guardar Credenciales"**
6. El sistema probará automáticamente la conexión

## 📊 Funcionalidades Disponibles

### Ver Balances en Tiempo Real

- Navega a **Binance → Ver Balances**
- Verás una tabla con todos tus activos:
  - Cantidad disponible y bloqueada
  - Precio actual en USD y ARS
  - Valor total de cada activo
  - Total de tu portafolio

### Actualizar Precios de Inversiones

Si tienes inversiones de Binance registradas en la sección "Inversiones":

1. Ve a **Inversiones**
2. Haz clic en **"🔄 Actualizar Precios en Tiempo Real"**
3. El sistema usará la API de Binance para actualizar los precios

### Sincronizar Balances con Inversiones

Para importar automáticamente tus balances de Binance como inversiones:

1. Ve a **Binance → Ver Balances**
2. Haz clic en **"🔄 Sincronizar con Inversiones"**
3. El sistema creará o actualizará inversiones automáticamente

## 🔐 Seguridad

### Mejores Prácticas

- ✅ Solo habilita permisos de **lectura (Read)** en las API Keys
- ✅ Nunca compartas tus API Keys con nadie
- ✅ Las credenciales se almacenan en la base de datos local
- ✅ Revoca las API Keys si sospechas que fueron comprometidas
- ❌ NUNCA habilites permisos de Trading o Withdrawals

### ¿Qué puede hacer la aplicación?

Con los permisos de solo lectura, Cash Track puede:
- ✅ Ver tus balances
- ✅ Obtener precios de mercado
- ✅ Consultar información de tu cuenta

Cash Track **NO PUEDE**:
- ❌ Realizar transacciones
- ❌ Retirar fondos
- ❌ Realizar trades
- ❌ Modificar tu cuenta

## 🧪 Modo Testnet

Binance ofrece un entorno de pruebas (Testnet) para desarrolladores:

1. Crea una cuenta en [Binance Testnet](https://testnet.binance.vision/)
2. Obtén API Keys del testnet
3. En Cash Track, marca la opción **"🧪 Usar Binance Testnet"**
4. Ingresa las credenciales del testnet

## 🔧 Solución de Problemas

### Error: "No se pudo conectar con Binance"

- Verifica que tus API Keys sean correctas
- Asegúrate de que la API Key esté activa en Binance
- Verifica que tengas los permisos de lectura habilitados
- Revisa tu conexión a internet

### Error: "API Keys inválidas"

- Verifica que copiaste correctamente la API Key y Secret
- Asegúrate de no haber incluido espacios al inicio o final
- Verifica que la API Key no haya sido revocada en Binance

### No aparecen balances

- Verifica que tengas fondos en tu cuenta de Binance
- Asegúrate de que la API Key tenga permisos de lectura de cuenta
- Intenta hacer clic en "🔄 Actualizar"

## 📝 Notas Técnicas

### APIs Utilizadas

- **Binance API v3** - Para obtener balances y precios
- **Exchange Rate API** - Para conversión USD/ARS
- **python-binance** - Librería oficial de Python para Binance

### Limitaciones

- Los precios se actualizan en tiempo real al hacer clic en el botón
- La tasa de cambio USD/ARS se aproxima al dólar blue/MEP
- Binance API tiene límites de tasa (rate limits) que la aplicación respeta

### Almacenamiento de Datos

Las credenciales se almacenan en la tabla `binance_credentials`:
```sql
CREATE TABLE binance_credentials (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    api_key TEXT NOT NULL,
    api_secret TEXT NOT NULL,
    is_testnet BOOLEAN DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

## 🆘 Soporte

Si tienes problemas con la integración de Binance:

1. Verifica la configuración de tus API Keys
2. Revisa los logs de la aplicación
3. Prueba la conexión desde la página de configuración
4. Consulta la documentación de Binance API

## 📚 Recursos Adicionales

- [Documentación oficial de Binance API](https://binance-docs.github.io/apidocs/)
- [python-binance en GitHub](https://github.com/sammchardy/python-binance)
- [Binance Testnet](https://testnet.binance.vision/)

---

**Última actualización**: Enero 2026
**Versión**: 1.0.0
