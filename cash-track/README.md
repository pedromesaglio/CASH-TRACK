# 💰 Cash Track - Gestor de Finanzas Personales con IA

Cash Track es una aplicación web moderna y completa para gestionar tus finanzas personales, con inteligencia artificial integrada para análisis automáticos, predicciones y recomendaciones personalizadas.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0.0-green.svg)
![Ollama](https://img.shields.io/badge/Ollama-AI-purple.svg)
![SQLite](https://img.shields.io/badge/SQLite-3-lightgrey.svg)

## ✨ Características Principales

### 📊 Gestión Financiera
- **Dashboard Interactivo**: Visualiza tus ingresos, gastos y balance en tiempo real
- **Gestión de Gastos**: Registra gastos con categorías visuales e iconos
- **Gestión de Ingresos**: Registra ingresos con conversión USD a ARS
- **Gestión de Inversiones**: Controla tus inversiones en diferentes plataformas
- **Categorías Personalizadas**: Crea tus propias categorías con iconos emoji
- **Filtros por Fecha**: Filtra transacciones por mes y año
- **Exportación CSV**: Exporta tus datos financieros
- **Sistema Multiusuario**: Usuarios independientes con datos aislados
- **Panel de Administración**: Gestiona usuarios y roles (admin/user)

### 🤖 Inteligencia Artificial Integrada

#### 1. Asistente Financiero Personal
- Chat interactivo con contexto financiero
- Responde preguntas sobre tus finanzas
- Consejos personalizados basados en tus datos

#### 2. Análisis Automático de Gastos
- Identifica patrones de gasto
- Analiza categorías con mayor inversión
- Genera insights y recomendaciones

#### 3. Categorización Inteligente
- Sugerencia automática de categorías
- Aprende de tus categorizaciones anteriores
- Mejora la velocidad de registro de gastos

#### 4. Predicciones y Alertas
- Predice gastos futuros basándose en histórico
- Compara con meses anteriores
- Genera alertas de gastos inusuales

#### 5. Resumen Mensual con IA
- Resumen completo del mes
- Comparación con períodos anteriores
- Recomendaciones para el próximo mes

### 🎨 Diseño Moderno
- Interfaz intuitiva y responsive
- Gradientes y animaciones suaves
- Gráficos interactivos con Chart.js
- Dark patterns y efectos visuales

## 🚀 Requisitos Previos

### Software Necesario
- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Ollama (para funcionalidades de IA)

### Instalación de Ollama

#### En Linux (Ubuntu/Debian)
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

#### En macOS
```bash
brew install ollama
```

#### En Windows
Descarga el instalador desde: https://ollama.com/download/windows

### Verificar Instalación de Ollama
```bash
ollama --version
```

### Descargar el Modelo de IA
Después de instalar Ollama, descarga el modelo llama3.2:
```bash
ollama pull llama3.2
```

**Nota**: La descarga puede tardar varios minutos dependiendo de tu conexión a internet (el modelo pesa aproximadamente 2GB).

### Iniciar Ollama
Ollama debe estar ejecutándose antes de usar las funcionalidades de IA:
```bash
ollama serve
```

Deja este comando corriendo en una terminal. Ollama estará disponible en `http://localhost:11434`

## 📦 Instalación del Proyecto

### 1. Clonar o Descargar el Proyecto
```bash
cd /ruta/donde/quieras/el/proyecto
```

### 2. Crear Entorno Virtual (Recomendado)
```bash
python -m venv venv

# En Linux/macOS
source venv/bin/activate

# En Windows
venv\Scripts\activate
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

Si no existe `requirements.txt`, instala manualmente:
```bash
pip install Flask==3.0.0
pip install Werkzeug==3.0.0
pip install ollama
```

### 4. Inicializar Base de Datos
```bash
python database.py
```

Este comando creará la base de datos SQLite con las tablas necesarias y un usuario por defecto.

### 5. Ejecutar la Aplicación
```bash
python app.py
```

La aplicación estará disponible en: `http://localhost:5000`

## 🔑 Credenciales por Defecto

Al inicializar la base de datos, se crea un usuario administrador:

- **Usuario**: `admin`
- **Contraseña**: `admin`
- **Rol**: Administrador

⚠️ **Importante**: Cambia estas credenciales en producción por seguridad.

### Sistema Multiusuario

Cash Track soporta múltiples usuarios con datos completamente aislados:

- **Usuarios Regulares**: Pueden gestionar sus propias finanzas
- **Administradores**: Acceso al panel de administración para:
  - Ver lista de usuarios registrados
  - Cambiar roles (user ↔ admin)
  - Eliminar usuarios y sus datos
  - Estadísticas de uso por usuario

Cada usuario solo puede ver y modificar sus propios datos financieros.

## 🛠️ Estructura del Proyecto

```
cash-track/
│
├── app.py                      # Aplicación principal Flask
├── database.py                 # Configuración de base de datos
├── requirements.txt            # Dependencias del proyecto
├── cashtrack.db               # Base de datos SQLite (se crea al iniciar)
│
├── static/
│   └── css/
│       └── style.css          # Estilos CSS de la aplicación
│
└── templates/
    ├── base.html              # Plantilla base
    ├── login.html             # Página de inicio de sesión
    ├── register.html          # Página de registro
    ├── index.html             # Dashboard principal
    ├── expenses.html          # Gestión de gastos
    ├── income.html            # Gestión de ingresos
    └── investments.html       # Gestión de inversiones
```

## 🎯 Uso de la Aplicación

### Primer Inicio
1. Inicia sesión con las credenciales por defecto
2. Comienza a registrar tus gastos e ingresos
3. Explora el dashboard para ver tus estadísticas

### Gestión de Gastos
1. Ve a la sección "Gastos"
2. Selecciona una categoría visual
3. Escribe la descripción (puedes usar el botón 🤖 para sugerencias automáticas)
4. Ingresa el monto, fecha y medio de pago
5. Haz clic en "Agregar Gasto"

### Gestión de Ingresos
1. Ve a la sección "Ingresos"
2. Ingresa la fuente del ingreso
3. Ingresa el monto (puede ser en USD, se convertirá a ARS)
4. Selecciona la fecha
5. Haz clic en "Agregar Ingreso"

### Gestión de Inversiones
1. Ve a la sección "Inversiones"
2. Selecciona la plataforma de inversión
3. Ingresa el nombre, tipo y monto invertido
4. Opcionalmente, ingresa el valor actual para ver ganancias/pérdidas
5. Haz clic en "Agregar Inversión"

### Panel de Administración

Los usuarios con rol de **Administrador** verán un enlace "👑 Admin" en la navegación superior.

Funcionalidades del panel:
- **Lista de usuarios**: Ver todos los usuarios registrados con estadísticas
- **Cambiar roles**: Convertir usuarios en administradores y viceversa
- **Eliminar usuarios**: Borrar usuarios y todos sus datos financieros
- **Estadísticas**: Ver cantidad de gastos e ingresos por usuario

**Nota**: Un administrador no puede cambiar su propio rol ni eliminarse a sí mismo.

### Uso del Asistente de IA

#### Chat Interactivo
1. Haz clic en el botón flotante 🤖 en el dashboard
2. Escribe tus preguntas sobre finanzas
3. Recibe respuestas personalizadas basadas en tus datos

#### Análisis Automático
1. En el chat de IA, haz clic en "📊 Analizar mis Finanzas"
2. Espera unos segundos mientras la IA procesa
3. Recibe un análisis detallado de tus gastos e ingresos

#### Predicciones
1. Haz clic en "🔮 Predicciones y Alertas"
2. La IA analizará tus últimos 3 meses
3. Recibirás predicciones y alertas sobre gastos inusuales

#### Resumen Mensual
1. Haz clic en "📝 Resumen Mensual IA"
2. Obtendrás un resumen completo del mes actual
3. Incluye comparaciones y recomendaciones

#### Categorización Inteligente
1. Al agregar un gasto, escribe la descripción
2. Haz clic en el botón 🤖 junto al campo
3. La IA sugerirá automáticamente la categoría más apropiada

## 🔧 Configuración Avanzada

### Cambiar Puerto de Flask
Edita `app.py` en la última línea:
```python
app.run(debug=True, port=PUERTO_DESEADO)
```

### Cambiar Modelo de IA
Si quieres usar un modelo diferente de Ollama, edita las llamadas a `ollama.chat()` en `app.py`:
```python
response = ollama.chat(
    model='nombre-del-modelo',  # Cambia aquí
    messages=[...]
)
```

Modelos disponibles en Ollama:
- `llama3.2` (recomendado, 2GB)
- `llama3.2:1b` (más ligero, 1GB)
- `mistral` (alternativa, 4GB)
- `codellama` (para análisis técnicos)

Descarga modelos adicionales:
```bash
ollama pull nombre-del-modelo
```

### Configurar Tasa de Cambio USD/ARS
La tasa de cambio está hardcodeada en `app.py` (línea ~220):
```python
USD_TO_ARS = 1200  # Actualiza este valor
```

## 🐛 Solución de Problemas

### Ollama no responde
**Problema**: Las funcionalidades de IA no funcionan.

**Solución**:
1. Verifica que Ollama esté corriendo:
   ```bash
   curl http://localhost:11434/api/tags
   ```
2. Si no responde, inicia Ollama:
   ```bash
   ollama serve
   ```
3. Verifica que el modelo esté descargado:
   ```bash
   ollama list
   ```

### Error de conexión a base de datos
**Problema**: `sqlite3.OperationalError: unable to open database file`

**Solución**:
1. Verifica permisos del directorio
2. Ejecuta nuevamente:
   ```bash
   python database.py
   ```

### Error de importación de módulos
**Problema**: `ModuleNotFoundError: No module named 'flask'`

**Solución**:
```bash
pip install -r requirements.txt
```

### La IA es muy lenta
**Problema**: Las respuestas de la IA tardan mucho.

**Solución**:
1. Usa un modelo más ligero:
   ```bash
   ollama pull llama3.2:1b
   ```
2. Cambia el modelo en `app.py`
3. Si tienes GPU, Ollama la usará automáticamente

### Gráficos no se muestran
**Problema**: Las gráficas del dashboard no aparecen.

**Solución**:
1. Verifica la conexión a internet (Chart.js se carga desde CDN)
2. Revisa la consola del navegador (F12) para errores
3. Asegúrate de tener datos registrados

## 📊 Tecnologías Utilizadas

- **Backend**: Flask 3.0.0 (Python)
- **Base de Datos**: SQLite3
- **Frontend**: HTML5, CSS3, JavaScript
- **IA**: Ollama + llama3.2
- **Gráficos**: Chart.js
- **Autenticación**: Flask sessions + Werkzeug password hashing

## 🤝 Contribuir

¿Quieres mejorar Cash Track? ¡Contribuciones son bienvenidas!

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

## 🎓 Aprendizaje y Recursos

### Documentación Relevante
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Ollama Documentation](https://ollama.com/docs)
- [Chart.js Documentation](https://www.chartjs.org/docs/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)

### Próximas Características Planeadas
- [ ] Exportación a PDF
- [ ] Gráficos de tendencias temporales
- [ ] Presupuestos por categoría con alertas
- [x] Multi-usuario con roles (✅ Implementado)
- [ ] API REST para integración externa
- [ ] Notificaciones por email
- [ ] Tema oscuro
- [ ] App móvil (React Native)

## 💡 Consejos de Uso

1. **Registra gastos diariamente**: La IA funciona mejor con más datos
2. **Usa categorías consistentes**: Ayuda a la IA a aprender tus patrones
3. **Revisa el análisis mensual**: Toma decisiones basadas en datos
4. **Personaliza categorías**: Crea categorías que se ajusten a tu estilo de vida
5. **Exporta tus datos**: Haz backups regulares en CSV

## 📞 Soporte

¿Problemas o preguntas?

- Abre un Issue en GitHub
- Revisa la sección de Solución de Problemas
- Consulta la documentación de Ollama si es problema de IA

---

**¡Desarrollado con ❤️ usando Flask, Ollama y Python!**

*Cash Track - Toma control de tus finanzas con inteligencia artificial*
