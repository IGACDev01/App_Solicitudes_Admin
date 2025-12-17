# Sistema de Gestión de Solicitudes Administrativas - IGAC

## 📋 Descripción

Sistema web administrativo desarrollado con Streamlit para el **Instituto Geográfico Agustín Codazzi (IGAC)** que permite gestionar el ciclo de vida completo de solicitudes hechas por las diferentes territoriales del IGAC. El sistema se integra con SharePoint como base de datos backend mediante Microsoft Graph API y proporciona un dashboard interactivo para administradores de diferentes áreas (SAF y comunicaciones actualmente).

### ¿Qué hace este sistema?

Este sistema permite a los administradores de diferentes áreas del IGAC:

- ✅ **Ver y gestionar solicitudes** de su área en tiempo real
- ✅ **Cambiar el estado** de las solicitudes siguiendo flujos de trabajo validados
- ✅ **Filtrar y buscar** solicitudes por múltiples criterios (estado, fecha, solicitante, etc.)
- ✅ **Agregar comentarios** y documentación a cada solicitud
- ✅ **Exportar reportes** a Excel para análisis adicional
- ✅ **Ver estadísticas** y métricas del área en dashboards interactivos
- ✅ **Recibir y enviar notificaciones** por correo electrónico automáticamente

### Características Principales

- 🔐 **Control de acceso por área**: Cada administrador solo ve las solicitudes de su área
- 📊 **Dashboard de análisis**: Gráficos interactivos y métricas en tiempo real
- 🔄 **Sincronización con SharePoint**: Todos los cambios se guardan automáticamente en SharePoint
- 📧 **Notificaciones automáticas**: Envío de correos cuando cambia el estado de una solicitud
- 📁 **Exportación de datos**: Descarga de solicitudes filtradas en formato Excel
- 🛡️ **Validación de flujos**: El sistema previene cambios de estado inválidos

## 🔧 Requisitos Previos

Antes de comenzar, asegúrate de tener instalado:

### Software Requerido

1. **Python 3.8 o superior**
   - Descargar desde: https://www.python.org/downloads/
   - Durante la instalación, marcar "Add Python to PATH"
   - Verificar instalación: `python --version`

2. **Git** (para clonar el repositorio)
   - Descargar desde: https://git-scm.com/downloads
   - Verificar instalación: `git --version`

### Credenciales Necesarias

Necesitarás obtener las siguientes credenciales del administrador del sistema:

- **Credenciales Azure AD**:
  - `TENANT_ID`: ID del tenant de Azure
  - `CLIENT_ID`: ID de la aplicación registrada en Azure AD
  - `CLIENT_SECRET`: Secreto de la aplicación

- **URL de SharePoint**:
  - `SHAREPOINT_SITE_URL`: URL completa del sitio SharePoint

- **Credenciales SMTP** (para correos):
  - Servidor SMTP, puerto, usuario y contraseña

- **Credenciales de administrador** (una por proceso):
  - Usuario y contraseña para cada proceso (Almacén, Contabilidad, etc.)

## 📦 Instalación

Sigue estos pasos en orden para instalar el sistema en tu computadora:

### Paso 1: Clonar el Repositorio

```bash
# Navega a la carpeta donde quieres instalar el proyecto
cd C:\Users\TuUsuario\Documents

# Clona el repositorio
git clone [URL_DEL_REPOSITORIO]

# Entra a la carpeta del proyecto
cd App_Solicitudes_Admin
```

### Paso 2: Crear Entorno Virtual

Es importante usar un entorno virtual para aislar las dependencias del proyecto:

**En Windows:**
```bash
# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual
.venv\Scripts\activate

# Deberías ver (.venv) al inicio de tu línea de comandos
```

**En Linux/Mac:**
```bash
# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual
source .venv/bin/activate

# Deberías ver (.venv) al inicio de tu línea de comandos
```

### Paso 3: Instalar Dependencias

Con el entorno virtual activado:

```bash
# Instalar todas las dependencias del proyecto
pip install -r requirements.txt

# Esto instalará: streamlit, pandas, plotly, requests, openpyxl, etc.
# Puede tomar varios minutos
```

### Paso 4: Configurar Secretos

Este es el paso **MÁS IMPORTANTE**. Sin esta configuración, la aplicación no funcionará.

1. **Crear carpeta de configuración:**
   ```bash
   # Si no existe, crear la carpeta .streamlit
   mkdir .streamlit
   ```

2. **Crear archivo de secretos:**

   Crea el archivo `.streamlit/secrets.toml` con el siguiente contenido (reemplaza los valores con tus credenciales reales):

   ```toml
   # ========================================
   # Credenciales Azure AD / Microsoft Graph
   # ========================================
   TENANT_ID = "tu-tenant-id-aqui"
   CLIENT_ID = "tu-client-id-aqui"
   CLIENT_SECRET = "tu-client-secret-aqui"
   SHAREPOINT_SITE_URL = "https://tu-organizacion.sharepoint.com/sites/tu-sitio"

   # ========================================
   # Credenciales de Administrador - Almacén
   # ========================================
   admin_almacen_usuario = "admin.almacen@igac.gov.co"
   admin_almacen_password = "password_seguro_aqui"

   # ========================================
   # Credenciales de Administrador - Contabilidad
   # ========================================
   admin_contabilidad_usuario = "admin.contabilidad@igac.gov.co"
   admin_contabilidad_password = "password_seguro_aqui"

   # ========================================
   # Configuración SMTP para Correos
   # ========================================
   smtp_server = "smtp.office365.com"
   smtp_port = 587
   smtp_usuario = "notificaciones@igac.gov.co"
   smtp_password = "password_smtp_aqui"
   smtp_remitente = "Sistema de Solicitudes <notificaciones@igac.gov.co>"

   # Agregar más credenciales de administrador según sea necesario
   # para otros procesos según se requiera
   ```

3. **⚠️ IMPORTANTE - Seguridad:**
   - **NUNCA** compartas este archivo
   - **NUNCA** lo subas a Git (ya está en `.gitignore`)
   - Guarda una copia de respaldo en un lugar seguro
   - Cambia las contraseñas periódicamente

### Paso 5: Verificar Configuración

Verifica que todo esté configurado correctamente:

```bash
# Prueba importar el módulo principal
python -c "from Scripts.sharepoint_list_manager import GestorListasSharePoint; print('✅ Configuración correcta')"

# Si ves "✅ Configuración correcta", todo está bien
# Si ves un error, revisa que secrets.toml tenga todos los campos
```

## 🚀 Ejecutar la Aplicación

### Ejecución Básica

Con el entorno virtual activado:

```bash
# Asegúrate de estar en la carpeta del proyecto
cd C:\Users\TuUsuario\Documents\App_Solicitudes_Admin

# Activa el entorno virtual (si no está activado)
.venv\Scripts\activate

# Ejecuta la aplicación
streamlit run Scripts/main_admin.py

# La aplicación se abrirá automáticamente en tu navegador
# Por defecto en: http://localhost:8501
```

### Ejecución con Modo Debug

Si necesitas ver más información para depurar problemas:

```bash
streamlit run Scripts/main_admin.py --logger.level=debug
```

### Detener la Aplicación

Para detener la aplicación:
- Presiona `Ctrl + C` en la terminal
- O cierra la ventana de terminal

## 📁 Estructura del Proyecto

Entender la estructura te ayudará a navegar y modificar el proyecto:

```
App_Solicitudes_Admin/
│
├── 📂 Scripts/                          # 🔥 CÓDIGO PRINCIPAL
│   ├── main_admin.py                   # Punto de entrada - EMPIEZA AQUÍ
│   ├── admin_solicitudes.py            # Interfaz de gestión de solicitudes
│   ├── dashboard.py                    # Dashboard de análisis y reportes
│   ├── sharepoint_list_manager.py      # Conexión con SharePoint/Graph API
│   ├── email_manager.py                # Sistema de notificaciones por correo
│   ├── state_flow_manager.py           # Validación de flujos de trabajo
│   ├── shared_cache_utils.py           # Utilidades de caché
│   ├── shared_filter_utils.py          # Utilidades de filtrado
│   ├── shared_html_utils.py            # Utilidades HTML (seguridad)
│   ├── shared_timezone_utils.py        # Manejo de zona horaria Colombia
│   └── utils.py                        # Utilidades generales
│
├── 📂 Data/                             # Archivos de datos
│   └── my_organization_emails.xlsx     # Lista de correos (ejemplo)
│
├── 📂 Theme/                            # Recursos visuales
│   └── Logo IGAC.png                   # Logo oficial IGAC
│
├── 📂 .streamlit/                       # ⚙️ CONFIGURACIÓN (NO EN GIT)
│   ├── config.toml                     # Configuración de Streamlit
│   └── secrets.toml                    # ⚠️ CREDENCIALES - NO COMPARTIR
│
├── 📂 .venv/                            # Entorno virtual Python (NO EN GIT)
│
├── requirements.txt                     # Dependencias del proyecto
├── .gitignore                          # Archivos ignorados por Git
└── README.md                           # 👈 ESTÁS AQUÍ
```

### Archivos Clave para Modificar

Si necesitas hacer cambios, estos son los archivos más importantes:

| Archivo | Cuándo Modificarlo |
|---------|-------------------|
| `Scripts/main_admin.py` | Cambiar apariencia general, colores, layout |
| `Scripts/admin_solicitudes.py` | Agregar campos a la vista de solicitudes |
| `Scripts/state_flow_manager.py` | Modificar estados o flujos de trabajo |
| `Scripts/email_manager.py` | Cambiar plantillas de correo |
| `.streamlit/secrets.toml` | Actualizar credenciales o agregar procesos |
| `.streamlit/config.toml` | Cambiar tema, colores, configuración de Streamlit |

## 🎮 Guía de Uso

### Para Administradores del Sistema

#### Primer Inicio de Sesión

1. **Abre la aplicación** (ver sección "Ejecutar la Aplicación")
2. Verás la pantalla principal con el logo IGAC
3. Haz clic en la pestaña **"⚙️ Administrar Solicitudes"**
4. Ingresa tus credenciales de área
5. Una vez autenticado, verás las solicitudes de tu área

#### Gestionar una Solicitud

1. **Ver solicitudes**: La tabla muestra todas las solicitudes de tu área
2. **Filtrar**: Usa los filtros en la barra lateral para buscar solicitudes específicas
   - Por estado (Asignada, En Proceso, etc.)
   - Por rango de fechas
   - Por solicitante
3. **Cambiar estado**:
   - Selecciona una solicitud
   - Elige el nuevo estado del menú desplegable
   - Agrega un comentario (opcional pero recomendado)
   - Haz clic en "Actualizar Estado"
4. **Ver historial**: Cada solicitud muestra su historial completo de cambios

#### Estados Disponibles

El sistema maneja 5 estados para las solicitudes:

1. **🟡 Asignada**: Solicitud nueva, asignada a tu área
   - Puedes cambiar a: "En Proceso", "Incompleta", o "Cancelada"

2. **🔵 En Proceso**: Estás trabajando activamente en la solicitud
   - Puedes cambiar a: "Completada", "Incompleta", o "Cancelada"

3. **🟠 Incompleta**: Pausada, esperando información del solicitante
   - Puedes cambiar a: "En Proceso" o "Cancelada"

4. **✅ Completada**: Solicitud finalizada exitosamente
   - Estado final, no se puede cambiar

5. **❌ Cancelada**: Solicitud cancelada
   - Estado final, no se puede cambiar

#### Exportar Reportes

1. Filtra las solicitudes que necesitas
2. Haz clic en el botón **"📥 Exportar a Excel"**
3. El archivo se descargará automáticamente
4. Abre con Excel para análisis adicional

#### Ver Dashboard de Análisis

1. Haz clic en la pestaña **"📊 Dashboard"**
2. Verás gráficos interactivos:
   - Distribución de solicitudes por estado
   - Solicitudes por área
   - Tendencias temporales
   - Métricas de rendimiento
3. Los gráficos son interactivos (puedes hacer zoom, filtrar, etc.)

### Para Desarrolladores

#### Modificar Estados del Flujo de Trabajo

Edita `Scripts/state_flow_manager.py`:

```python
STATE_TRANSITIONS = {
    "Tu_Nuevo_Estado": {
        "allowed": ["Estado_Destino_1", "Estado_Destino_2"],
        "description": "Puede moverse a: Estado_Destino_1, Estado_Destino_2"
    }
}
```

#### Agregar una nueva área

1. Edita `.streamlit/secrets.toml`:
   ```toml
   admin_nuevo_area_usuario = "admin.nuevo@igac.gov.co"
   admin_nuevo_area_password = "password_aqui"
   ```

2. Actualiza la lógica de autenticación en `Scripts/admin_solicitudes.py`

3. Reinicia la aplicación

#### Cambiar Colores y Tema

Edita `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#006AB3"        # Color principal (azul IGAC)
backgroundColor = "#FFFFFF"      # Fondo blanco
secondaryBackgroundColor = "#F0F2F6"  # Gris claro
textColor = "#262730"           # Texto oscuro
```

#### Depurar Problemas

1. **Ver logs en consola**: La aplicación imprime mensajes de debug en la terminal
2. **Modo debug**: Ejecuta con `--logger.level=debug`
3. **Inspeccionar datos SharePoint**:
   ```python
   from Scripts.sharepoint_list_manager import GestorListasSharePoint
   gestor = GestorListasSharePoint(nombre_lista="Data App Solicitudes")
   print(gestor.df.head())  # Ver primeras 5 solicitudes
   ```

## 🐛 Resolución de Problemas Comunes

### Problema 1: "La aplicación no inicia"

**Síntomas**: Error al ejecutar `streamlit run Scripts/main_admin.py`

**Soluciones**:

1. ✅ Verifica que el entorno virtual esté activado:
   ```bash
   # Deberías ver (.venv) al inicio de tu línea de comandos
   .venv\Scripts\activate
   ```

2. ✅ Verifica que todas las dependencias estén instaladas:
   ```bash
   pip install -r requirements.txt
   ```

3. ✅ Verifica que existe `.streamlit/secrets.toml`:
   ```bash
   # Windows
   dir .streamlit\secrets.toml

   # Linux/Mac
   ls -la .streamlit/secrets.toml
   ```

4. ✅ Verifica que Python sea versión 3.8+:
   ```bash
   python --version
   ```

### Problema 2: "Error de conexión con SharePoint"

**Síntomas**: Mensaje "❌ SharePoint: Error de conexión"

**Soluciones**:

1. ✅ Verifica credenciales en `.streamlit/secrets.toml`:
   - `TENANT_ID` correcto
   - `CLIENT_ID` correcto
   - `CLIENT_SECRET` correcto
   - `SHAREPOINT_SITE_URL` es la URL completa del sitio

2. ✅ Verifica permisos de la aplicación Azure AD:
   - Debe tener "Directory.Read.All"
   - Debe tener "Sites.ReadWrite.All"

3. ✅ Verifica conectividad de red:
   ```bash
   ping graph.microsoft.com
   ```

### Problema 3: "Los cambios no se reflejan en la UI"

**Síntomas**: Actualizas una solicitud pero no ves el cambio

**Solución**:

El problema es el caché. El sistema cachea datos por 5 minutos para rendimiento.

```python
# Si estás modificando código, agrega después de actualizar:
invalidar_cache_datos()
st.rerun()
```

O simplemente **espera 5 minutos** para que expire el caché automáticamente.

### Problema 4: "Error 'ModuleNotFoundError'"

**Síntomas**: `ModuleNotFoundError: No module named 'streamlit'` o similar

**Solución**:

```bash
# Asegúrate de que el entorno virtual esté activado
.venv\Scripts\activate

# Reinstala dependencias
pip install -r requirements.txt

# Verifica instalación
pip list | grep streamlit
```

### Problema 5: "Fechas muestran hora incorrecta"

**Síntomas**: Las fechas están 5 horas adelante o atrás

**Causa**: Problema de conversión UTC/Colombia

**Solución**:

El código debe usar funciones de `shared_timezone_utils.py`:

```python
from shared_timezone_utils import obtener_fecha_actual_colombia

# Correcto
fecha = obtener_fecha_actual_colombia()

# Incorrecto (no uses)
fecha = datetime.now()  # Esto usa UTC
```


## 📊 Rendimiento y Optimización

### Caché de Datos

El sistema usa caché agresivo para mejorar rendimiento:

- **Datos de SharePoint**: Se cachean por 5 minutos
- **Conexión SharePoint**: Se cachea durante toda la sesión
- **Tokens de acceso**: Se cachean hasta que expiran

### Datasets Grandes

Si tienes más de 1000 solicitudes:
- El sistema automáticamente optimiza el uso de memoria
- Solo carga campos esenciales en la vista inicial
- Los detalles completos se cargan al seleccionar una solicitud

### Monitorear Rendimiento

Observa los logs en la consola:
```
📊 Datos en caché | Total solicitudes: 250 | Actualizado: 10:30:15 | Cache TTL: 300s
⚠️ Large dataset detected (1500 records), optimizing memory usage
```

### Permisos Azure AD

La aplicación registrada en Azure AD debe tener:

```
Microsoft Graph API Permissions:
- Directory.Read.All (Delegated)
- Sites.ReadWrite.All (Application)
```

## 🤝 Contribuir al Proyecto

### Para Reportar Problemas

1. Verifica que el problema no esté ya resuelto en esta documentación
2. Describe el problema detalladamente:
   - ¿Qué estabas haciendo?
   - ¿Qué esperabas que pasara?
   - ¿Qué pasó en realidad?
   - ¿Hay mensajes de error? (cópialos completos)
3. Incluye información del sistema:
   - Versión de Python: `python --version`
   - Sistema operativo
   - Navegador usado

### Para Agregar Funcionalidades

1. **Crea una rama nueva**:
   ```bash
   git checkout -b feature/nombre-de-tu-funcionalidad
   ```

2. **Desarrolla tu funcionalidad**:
   - Sigue las convenciones de código existentes
   - Usa nombres de variables en español (consistencia con el código actual)
   - Agrega comentarios explicativos
   - Documenta funciones con docstrings

3. **Prueba localmente**:
   - Ejecuta la aplicación y verifica que funciona
   - Prueba diferentes escenarios
   - Verifica que no rompe funcionalidad existente

4. **Documenta cambios**:
   - Actualiza este README si es necesario
   - Actualiza `Docs/CLAUDE.md` si cambias arquitectura
   - Agrega comentarios en el código

5. **Commit y push**:
   ```bash
   git add .
   git commit -m "Descripción clara del cambio"
   git push origin feature/nombre-de-tu-funcionalidad
   ```

6. **Crea Pull Request** para revisión

### Convenciones de Código

- **Nombres de variables y funciones**: En español (ej: `obtener_datos`, `nombre_solicitante`)
- **Comentarios**: En español
- **Indentación**: 4 espacios
- **Imports**: Agrupados (stdlib, third-party, local)
- **Type hints**: Usar cuando sea posible

Ejemplo:
```python
def obtener_solicitudes_por_estado(estado: str) -> pd.DataFrame:
    """
    Obtiene todas las solicitudes filtradas por estado.

    Args:
        estado: Estado de la solicitud ('Asignada', 'En Proceso', etc.)

    Returns:
        DataFrame con las solicitudes filtradas
    """
    # Implementación aquí
    pass
```

## 📚 Recursos Adicionales

### Documentación Interna

- **`Docs/CLAUDE.md`**: Documentación técnica completa para desarrolladores

### Documentación Externa

- **Streamlit**: https://docs.streamlit.io/
- **Microsoft Graph API**: https://docs.microsoft.com/en-us/graph/
- **SharePoint REST API**: https://docs.microsoft.com/en-us/sharepoint/dev/sp-add-ins/
- **Pandas**: https://pandas.pydata.org/docs/
- **Plotly**: https://plotly.com/python/

---

## 🎯 Inicio Rápido (Resumen)

Si ya conoces el proyecto y solo necesitas recordar los comandos:

```bash
# 1. Activar entorno
.venv\Scripts\activate

# 2. Ejecutar aplicación
streamlit run Scripts/main_admin.py

# 3. Abrir en navegador
# http://localhost:8501

# 4. Iniciar sesión con credenciales de área/proceso

# 5. Gestionar solicitudes
```

---

