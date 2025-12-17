# CLAUDE.md

Este archivo proporciona orientación a Claude Code (claude.ai/code) cuando trabaja con código en este repositorio.

## Descripción General del Proyecto

**App_Solicitudes_Admin** es un sistema de gestión de solicitudes administrativas basado en Streamlit para el Instituto Geográfico Agustín Codazzi (IGAC). Es un dashboard administrativo que gestiona solicitudes hechas por las diferentes territoriales del IGAC a través de diversos flujos de trabajo, utilizando SharePoint como almacén de datos backend mediante Microsoft Graph API.

**Características principales:**
- Gestión del ciclo de vida de solicitudes a través de 13 procesos de dos áreas principales (SAF y Comunicaciones)
- Integración con SharePoint mediante Microsoft Graph API
- Notificaciones por correo electrónico para transiciones de estado
- Control de acceso basado en roles por área
- Filtrado, búsqueda y análisis de solicitudes
- Funcionalidad de exportación a Excel
- Manejo de zona horaria para la región de Colombia (COT)

## Comandos de Desarrollo

### Ejecutar la Aplicación

```bash
# Activar entorno virtual (Windows)
.venv\Scripts\activate

# Activar entorno virtual (Linux/Mac)
source .venv/bin/activate

# Ejecutar el dashboard administrativo principal
streamlit run Scripts/main_admin.py

# Ejecutar con logging de depuración
streamlit run Scripts/main_admin.py --logger.level=debug
```

### Gestión de Dependencias

```bash
# Instalar/actualizar dependencias
.venv\Scripts\activate
pip install -r requirements.txt
```

## Arquitectura del Sistema

### Estructura de Alto Nivel

```
App_Solicitudes_Admin/
├── Scripts/                         # Código principal de la aplicación
│   ├── main_admin.py               # Punto de entrada Streamlit - dashboard principal
│   ├── admin_solicitudes.py        # Gestión de solicitudes y transiciones de estado
│   ├── dashboard.py                # Vistas de análisis y reportes
│   ├── sharepoint_list_manager.py  # Integración SharePoint/Graph API
│   ├── email_manager.py            # Sistema de notificaciones por correo
│   ├── state_flow_manager.py       # Máquina de estados del flujo de trabajo
│   ├── shared_cache_utils.py       # Utilidades de caché
│   ├── shared_filter_utils.py      # Utilidades de filtrado
│   ├── shared_html_utils.py        # Utilidades HTML (seguridad)
│   ├── shared_timezone_utils.py    # Manejo de zona horaria Colombia
│   └── utils.py                    # Utilidades generales
├── Data/                           # Archivos de datos
├── Theme/                          # Archivos de tema personalizado Streamlit
├── Docs/                           # Documentación
├── .streamlit/                     # Configuración de Streamlit
│   ├── config.toml                # Configuración de la aplicación
│   └── secrets.toml               # Credenciales (NO en git)
└── requirements.txt                # Dependencias Python
```

### Flujo de Datos y Aplicación

#### 1. Punto de Entrada: `Scripts/main_admin.py`

Es el archivo principal de la aplicación Streamlit que:

- Inicializa la configuración de página (layout ancho, barra de herramientas mínima)
- Configura CSS personalizado con marca IGAC (colores: #006AB3 primario, #38a962 footer)
- Crea instancia cacheada de `GestorListasSharePoint` para conexión SharePoint
- Implementa caché de datos SharePoint con TTL de 5 minutos
- Carga de forma lazy los módulos de pestañas (admin_solicitudes, dashboard) según selección del usuario
- Ejecuta mantenimiento periódico cada 30 minutos usando `periodic_maintenance()` de shared_cache_utils

**Funciones clave:**
```python
# Caché de datos con TTL de 5 minutos
@st.cache_data(ttl=300, show_spinner=False, max_entries=3)
def obtener_datos_sharepoint_en_cache(cache_key: str = "default"):
    # Retorna datos cacheados de SharePoint

# Caché de recursos para conexión SharePoint
@st.cache_resource
def obtener_gestor_datos():
    return GestorListasSharePoint(nombre_lista="Data App Solicitudes")
```

#### 2. Fuente de Datos: `Scripts/sharepoint_list_manager.py`

Gestiona todas las interacciones con SharePoint y Microsoft Graph API:

**Clase principal: `GestorListasSharePoint`**
- Autenticación OAuth2 usando tenant_id, client_id, client_secret desde secrets
- Caché de tokens de acceso con seguimiento de expiración para minimizar llamadas API
- Lógica de reintentos: 3 intentos con backoff exponencial para resiliencia API
- Lista principal de SharePoint: "Data App Solicitudes"
- Timeout de 30 segundos en peticiones para prevenir bloqueos

**Características de manejo de errores:**
- Manejo específico de códigos de error HTTP (400, 401, 403, 429, 500, 503)
- Logging detallado de errores para depuración
- Reintentos automáticos con delays incrementales (1s, 2s, 4s)

#### 3. Gestión de Estados: `Scripts/state_flow_manager.py`

Implementa la máquina de estados del flujo de trabajo de solicitudes:

**Clase `StateFlowValidator`:**
- Valida transiciones de estado según reglas de negocio
- Define estados válidos: `Asignada`, `En Proceso`, `Incompleta`, `Completada`, `Cancelada`
- Estados terminales (no pueden transicionar): `Completada`, `Cancelada`

**Transiciones permitidas:**
```python
STATE_TRANSITIONS = {
    "Asignada": {
        "allowed": ["En Proceso", "Incompleta", "Cancelada"],
        "description": "Puede moverse a: En Proceso (iniciar trabajo), Incompleta (pausar), o Cancelada"
    },
    "En Proceso": {
        "allowed": ["Completada", "Incompleta", "Cancelada"],
        "description": "Puede moverse a: Completada (finalizar), Incompleta (pausar para info), o Cancelada"
    },
    "Incompleta": {
        "allowed": ["En Proceso", "Cancelada"],
        "description": "Puede resumir a: En Proceso (continuar trabajo) o Cancelada"
    },
    "Completada": {
        "allowed": [],
        "description": "Estado terminal - no puede transicionar"
    },
    "Cancelada": {
        "allowed": [],
        "description": "Estado terminal - no puede transicionar"
    }
}
```

**Clase `StateHistoryTracker`:**
- Rastrea y gestiona el historial de cambios de estado
- Formato de entrada: `[DD/MM/YYYY HH:MM:SS COT] Estado`
- Mantiene historial completo de transiciones con timestamps

#### 4. Interfaz de Gestión: `Scripts/admin_solicitudes.py`

Proporciona la interfaz de usuario para administración de solicitudes:

- Visualización de solicitudes con filtrado y búsqueda
- Edición en línea de campos de solicitud
- UI de transición de estado con validación
- Funcionalidad de exportación a Excel
- Control de acceso basado en roles por área
- **Credenciales cargadas exclusivamente desde secrets.toml** (sin credenciales hardcodeadas)

#### 5. Sistema de Notificaciones: `Scripts/email_manager.py`

Gestiona notificaciones por correo electrónico:

- Envía notificaciones automáticas en transiciones de estado
- Usa configuración SMTP desde secrets
- Plantillas de correo personalizables

#### 6. Dashboard de Análisis: `Scripts/dashboard.py`

Proporciona vistas de análisis y reportes:

- Gráficos y estadísticas de solicitudes
- Métricas de procesos por área
- Visualizaciones con Plotly
- Filtros interactivos

### Módulos Utilitarios

**`shared_cache_utils.py`**: Gestión de claves de caché e invalidación
- `invalidar_cache_datos()`: Limpia caché de datos
- `forzar_actualizacion_cache()`: Genera nueva clave para forzar refresh
- `obtener_cache_key()`: Obtiene clave actual de caché
- `invalidar_y_actualizar_cache()`: Combinación de invalidar y actualizar
- `cleanup_old_session_data()`: Limpia datos de sesión antiguos
- `periodic_maintenance()`: Mantenimiento periódico de caché y sesión

**`shared_filter_utils.py`**: Lógica de filtrado de DataFrames
- Implementa filtros por estado, proceso, área, fechas
- Búsqueda de texto en múltiples campos

**`shared_html_utils.py`**: Sanitización de contenido HTML (previene XSS)
- `limpiar_contenido_html()`: Elimina etiquetas y scripts peligrosos
- `formatear_comentarios_administrador_para_mostrar()`: Renderizado HTML seguro

**`shared_timezone_utils.py`**: Conversiones de zona horaria Colombia (COT/UTC)
- `obtener_fecha_actual_colombia()`: Obtiene fecha actual en hora de Colombia
- `convertir_a_colombia()`: Convierte UTC → Colombia
- `convertir_a_utc_para_almacenamiento()`: Convierte Colombia → UTC (para SharePoint)
- `formatear_fecha_colombia()`: Formatea fechas en formato colombiano

**`utils.py`**: Cálculos de tiempo para estados de solicitudes
- `calcular_tiempo_pausa_solicitud_individual()`: Calcula tiempo de pausa total
- `calcular_tiempo_pausa_en_tiempo_real()`: Calcula mediana de tiempos de pausa
- `calcular_incompletas_con_tiempo_real()`: Solicitudes incompletas con tiempo real
- `aplicar_tiempos_pausa_tiempo_real_dataframe()`: Aplica cálculos a DataFrame

## Modelo de Datos

La lista de SharePoint "Data App Solicitudes" contiene registros de solicitudes con los siguientes campos clave:

### Campos Principales

- **`id_solicitud`**: ID único de solicitud (string)
- **`nombre_solicitante`**: Nombre del solicitante
- **`email_solicitante`**: Correo electrónico del solicitante
- **`fecha_solicitud`**: Fecha de creación de la solicitud (datetime)
- **`tipo_solicitud`**: Tipo de solicitud
- **`estado`**: Estado actual del flujo de trabajo (uno de VALID_STATES)
- **`proceso`**: Proceso específico (ej. "Almacén", "Contabilidad", "Comunicación Externa")
- **`area`**: Área administrativa ("Subdirección Administrativa y Financiera" o "Oficina Asesora de Comunicaciones")
- **`HistorialEstados`**: Historial de cambios de estado con timestamps
- Campos adicionales para comentarios, adjuntos, fechas, etc.

### Estados del Flujo de Trabajo

El sistema gestiona las transiciones de solicitudes a través de flujos de trabajo por área:

1. **Asignada**: Solicitud asignada, pendiente de iniciar
2. **En Proceso**: Trabajo activo en la solicitud
3. **Incompleta**: Pausada, esperando información adicional
4. **Completada**: Finalizada exitosamente (estado terminal)
5. **Cancelada**: Cancelada (estado terminal)

### Áreas y Procesos

**Subdirección Administrativa y Financiera (SAF):**
- Almacén
- Archivo
- Contabilidad
- Contractual
- Correspondencia
- Infraestructura
- Operación Logística SAF
- Presupuesto
- Tesorería
- Tiquetes
- Transporte

**Oficina Asesora de Comunicaciones:**
- Comunicación Externa
- Comunicación Interna

## Archivos de Configuración

### `.streamlit/config.toml`

Configuración de Streamlit:

```toml
[theme]
primaryColor = "#006AB3"  # Azul IGAC
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"

[server]
fileWatcherType = "none"  # Deshabilitado para rendimiento
enableCORS = false        # Deshabilitado para integración SharePoint
enableXsrfProtection = false

[runner]
fastReruns = false        # Previene problemas de carga de módulos
```

### `.streamlit/secrets.toml` (NO en git)

Credenciales sensibles y configuración:

```toml
# Credenciales Azure AD para Graph API
TENANT_ID = "tu-tenant-id"
CLIENT_ID = "tu-client-id"
CLIENT_SECRET = "tu-client-secret"
SHAREPOINT_SITE_URL = "https://tu-sitio.sharepoint.com/sites/nombre"

# Credenciales de administrador - Subdirección Administrativa y Financiera
admin_almacen_usuario = "usuario@ejemplo.com"
admin_almacen_password = "contraseña"
admin_archivo_usuario = "usuario@ejemplo.com"
admin_archivo_password = "contraseña"
admin_contabilidad_usuario = "usuario@ejemplo.com"
admin_contabilidad_password = "contraseña"
# ... más credenciales para otros procesos de SAF

# Credenciales de administrador - Oficina Asesora de Comunicaciones
admin_com_externa_usuario = "usuario@ejemplo.com"
admin_com_externa_password = "contraseña"
admin_com_interna_usuario = "usuario@ejemplo.com"
admin_com_interna_password = "contraseña"

# Configuración SMTP para notificaciones
smtp_server = "smtp.office365.com"
smtp_port = 587
smtp_usuario = "notificaciones@ejemplo.com"
smtp_password = "contraseña"
smtp_remitente = "Sistema de Solicitudes <notificaciones@ejemplo.com>"
```

## Patrones de Implementación Críticos

### 1. Gestión de Caché

La aplicación usa caché agresivo para rendimiento pero requiere invalidación cuidadosa:

```python
# Caché de datos con TTL de 5 minutos
@st.cache_data(ttl=300, show_spinner=False, max_entries=3)
def obtener_datos_sharepoint_en_cache(cache_key: str = "default"):
    # Retorna datos cacheados de SharePoint
    pass

# Caché de recursos para conexión SharePoint
@st.cache_resource
def obtener_gestor_datos():
    return GestorListasSharePoint(nombre_lista="Data App Solicitudes")
```

**CRÍTICO**: Después de cualquier operación de escritura a SharePoint, DEBE invalidar el caché:

```python
# Después de actualizar datos en SharePoint
from shared_cache_utils import invalidar_cache_datos
invalidar_cache_datos()  # o st.cache_data.clear()
st.rerun()  # Forzar actualización de UI con nuevos datos
```

Si no invalida el caché, los cambios no aparecerán en la UI hasta que expire el TTL de 5 minutos.

### 2. Manejo de Zona Horaria

**SIEMPRE use las funciones de zona horaria de Colombia** desde `shared_timezone_utils.py`:

```python
from shared_timezone_utils import (
    obtener_fecha_actual_colombia,     # Obtener hora actual de Colombia
    convertir_a_colombia,              # UTC → Colombia
    convertir_a_utc_para_almacenamiento  # Colombia → UTC (para SharePoint)
)

# Ejemplo: Obtener timestamp actual
fecha_actual = obtener_fecha_actual_colombia()

# Ejemplo: Almacenar fecha en SharePoint (debe ser UTC)
fecha_utc = convertir_a_utc_para_almacenamiento(fecha_colombia)
```

**Nunca use la hora UTC predeterminada de Python directamente** - todas las fechas deben estar en hora de Colombia para visualización y UTC para almacenamiento.

### 3. Validación de Transiciones de Estado

Los cambios de estado de solicitudes se validan mediante `StateFlowValidator`:

```python
from state_flow_manager import StateFlowValidator, validate_and_get_transition_message

# Validar antes de intentar cambio de estado
is_valid, message = validate_and_get_transition_message(
    estado_actual="Asignada",
    nuevo_estado="En Proceso"
)

if is_valid:
    # Proceder con cambio de estado
    pass
else:
    st.error(message)
```

**Estados válidos**: `Asignada`, `En Proceso`, `Incompleta`, `Completada`, `Cancelada`

**Estados terminales** (no pueden transicionar): `Completada`, `Cancelada`

### 4. Sanitización de HTML

El contenido HTML proporcionado por usuarios DEBE sanitizarse para prevenir XSS:

```python
from shared_html_utils import limpiar_contenido_html, formatear_comentarios_administrador_para_mostrar

# Limpiar HTML antes de almacenar
comentario_limpio = limpiar_contenido_html(comentario_usuario)

# Formatear para visualización segura en Streamlit
html_seguro = formatear_comentarios_administrador_para_mostrar(comentario)
st.markdown(html_seguro, unsafe_allow_html=True)
```

### 5. Autenticación y Secretos

**NUNCA codifique credenciales en duro**. Siempre use `st.secrets`:

```python
# Correcto
tenant_id = st.secrets["TENANT_ID"]

# Incorrecto - NUNCA haga esto
tenant_id = "abc123-hardcoded"
```

La autenticación de SharePoint usa flujo de credenciales de cliente OAuth2. El login de administrador usa email/contraseña específicos por proceso desde secrets.

**Nota importante**: El código ha sido limpiado para eliminar todas las credenciales hardcodeadas. Ahora TODAS las credenciales deben provenir exclusivamente de `.streamlit/secrets.toml`.

### 6. Manejo de Errores

Use las funciones de visualización de Streamlit para errores de cara al usuario:

```python
try:
    # Operación SharePoint
    gestor.actualizar_solicitud(...)
except Exception as e:
    st.error(f"❌ Error actualizando solicitud: {e}")  # El usuario ve esto
    print(f"Debug: {e}")  # Va a consola/logs
```

Los errores de conexión se registran pero la aplicación puede continuar con datos cacheados cuando sea posible.

## Tareas Comunes de Desarrollo

### Agregar una Nueva Transición de Estado

Editar `Scripts/state_flow_manager.py`:

```python
STATE_TRANSITIONS = {
    "Estado_Nuevo": {
        "allowed": ["Estado_Destino_1", "Estado_Destino_2"],
        "description": "Puede moverse a: ..."
    }
}
```

### Depurar Conexión SharePoint

```python
from Scripts.sharepoint_list_manager import GestorListasSharePoint

gestor = GestorListasSharePoint(nombre_lista="Data App Solicitudes")
df = gestor.df
print(df.head())
```

**Problemas comunes:**
- `.streamlit/secrets.toml` faltante → Verificar que todas las claves requeridas existan
- Errores de token → Verificar que la app Azure AD tenga permisos Graph API (Directory.Read.All, Sites.ReadWrite.All)
- Throttling → Verificar cuotas de Graph API (la lógica de reintentos maneja fallos temporales)

### Agregar un Nuevo Proceso a un Área

1. Agregar credenciales en `.streamlit/secrets.toml`:
   ```toml
   admin_nuevo_proceso_usuario = "admin.nuevo@igac.gov.co"
   admin_nuevo_proceso_password = "password_aqui"
   ```

2. Actualizar el mapeo en `Scripts/admin_solicitudes.py` función `cargar_credenciales_administradores()`:
   ```python
   mapeo_procesos = {
       # ... procesos existentes
       "Nuevo Proceso": "admin_nuevo_proceso"
   }
   ```

3. Asignar el proceso al área correspondiente en la misma función

4. Reiniciar la aplicación

### Modificar Plantillas de Correo Electrónico

1. Editar `Scripts/email_manager.py`
2. Actualizar plantillas HTML para notificaciones
3. Probar con diferentes estados de transición
4. Verificar que los correos se envíen correctamente

## Limpieza de Código Realizada

Se han realizado las siguientes limpiezas en el código:

1. **Eliminado `timezone_utils_admin.py`**: Archivo duplicado y obsoleto, reemplazado por `shared_timezone_utils.py`

2. **Actualizado `utils.py`**: Cambiado el import de `timezone_utils_admin` a `shared_timezone_utils`

3. **Limpiado `main_admin.py`**:
   - Eliminada función duplicada `invalidar_cache_datos()` (ya existe en shared_cache_utils)
   - Eliminada función duplicada `cleanup_streamlit_cache()` (ya existe en shared_cache_utils)
   - Eliminada función duplicada `cleanup_old_session_data()` (ya existe en shared_cache_utils)
   - Eliminada función duplicada `periodic_maintenance()` (ya existe en shared_cache_utils)
   - Ahora importa `periodic_maintenance` desde shared_cache_utils

4. **Limpiado `shared_cache_utils.py`**:
   - Eliminados alias innecesarios para "compatibilidad con app de usuario"
   - Traducidos docstrings al español
   - Código más limpio y enfocado solo en la app de administración

5. **Limpiado `admin_solicitudes.py`**:
   - Eliminadas credenciales hardcodeadas en `_cargar_credenciales_defecto()`
   - Ahora las credenciales DEBEN venir exclusivamente de secrets.toml
   - Mejorado manejo de errores cuando faltan credenciales

## Pruebas

Actualmente no hay pruebas automatizadas configuradas. Flujo de pruebas manual:

1. Ejecutar `streamlit run Scripts/main_admin.py`
2. Probar diferentes estados y transiciones de solicitudes
3. Verificar actualizaciones en SharePoint vía Graph API
4. Verificar que se envíen notificaciones por correo
5. Validar comportamiento de caché (los cambios se reflejan después de invalidación)

## Resolución de Problemas

### La Aplicación No Inicia

1. Verificar que `.streamlit/secrets.toml` existe en la raíz del proyecto
2. Verificar Python 3.8+ en el entorno virtual
3. Verificar que todas las dependencias estén instaladas: `pip install -r requirements.txt`
4. Buscar errores de importación: `python -c "from Scripts.sharepoint_list_manager import GestorListasSharePoint"`

### Rendimiento Lento

- Los datos de SharePoint se cachean por 5 minutos (verificar cache_key y TTL)
- Conjuntos de datos grandes (1000+ registros) activan optimización de memoria
- Si las consultas son consistentemente lentas, verificar throttling de Graph API
- Considerar aumentar TTL del caché si los datos cambian con poca frecuencia

### Fallos de Conexión SharePoint

- Verificar que las credenciales en secrets sean correctas
- Verificar que la app Azure AD tenga permisos "Directory.Read.All" y "Sites.ReadWrite.All"
- Verificar que `SHAREPOINT_SITE_URL` coincida con el sitio SharePoint real
- La lógica de reintentos de token maneja fallos temporales; revisar logs para errores persistentes
- Verificar conectividad de red y firewall

### El Caché No Se Actualiza

Después de hacer cambios, invalidar explícitamente:

```python
from shared_cache_utils import invalidar_cache_datos
invalidar_cache_datos()  # o st.cache_data.clear()
st.rerun()
```

O forzar actualización de clave de caché:

```python
from shared_cache_utils import forzar_actualizacion_cache
cache_key = forzar_actualizacion_cache()
# La próxima llamada usará la nueva clave
```

### Errores de Carga de Módulos de Streamlit

Si ve errores de "dynamically imported module", asegurar que `fastReruns = false` en `.streamlit/config.toml`.

### Problemas de Zona Horaria

- Todas las fechas almacenadas en SharePoint deben estar en UTC
- Todas las fechas mostradas al usuario deben estar en hora de Colombia (COT)
- Siempre usar las funciones de `shared_timezone_utils.py`
- Si ve diferencias de 5 horas, probablemente hay un problema de conversión UTC/COT

### Error de Credenciales Faltantes

Si ve el error "No se encontraron credenciales de administrador en secrets.toml":

1. Verificar que `.streamlit/secrets.toml` existe
2. Verificar que tiene todas las credenciales necesarias para los procesos
3. Verificar el formato correcto de las claves (ej: `admin_almacen_usuario`)
4. Reiniciar la aplicación después de agregar credenciales

## Dependencias Clave

```txt
# Framework web
streamlit==1.32.0

# Manejo de zona horaria
pytz==2023.3

# Manipulación y análisis de datos
pandas>=1.5.0
numpy>=1.24.0

# Gráficos y visualización
plotly>=5.15.0

# Peticiones HTTP y llamadas API
requests>=2.31.0

# Manejo de archivos Excel
openpyxl>=3.1.0
xlsxwriter>=3.1.0
```

## Mejores Prácticas

### Seguridad

1. **NUNCA** comitear `.streamlit/secrets.toml` al repositorio
2. **SIEMPRE** sanitizar entrada de usuario antes de almacenar o mostrar
3. **USAR** funciones de `shared_html_utils.py` para contenido HTML de usuario
4. **VALIDAR** todas las transiciones de estado antes de aplicar
5. **ROTAR** credenciales periódicamente
6. **NO HARDCODEAR** credenciales en el código - usar solo secrets.toml

### Rendimiento

1. **APROVECHAR** el caché de Streamlit para operaciones costosas
2. **INVALIDAR** caché inmediatamente después de operaciones de escritura
3. **LIMITAR** tamaño de DataFrames para conjuntos de datos grandes (optimización en main_admin.py)
4. **MINIMIZAR** llamadas a Graph API usando caché de tokens
5. **MONITOREAR** uso de cuotas de Graph API

### Mantenibilidad

1. **DOCUMENTAR** cambios en flujos de estado en `state_flow_manager.py`
2. **MANTENER** consistencia en nomenclatura de funciones (español)
3. **USAR** type hints donde sea posible
4. **REGISTRAR** errores con contexto suficiente para depuración
5. **ACTUALIZAR** esta documentación cuando se agreguen características importantes
6. **EVITAR** código duplicado - usar funciones compartidas en módulos shared_*
7. **LIMPIAR** código no usado regularmente

### Control de Versiones

1. **COMMITEAR** cambios frecuentemente con mensajes descriptivos
2. **PROBAR** localmente antes de hacer push
3. **USAR** branches para características nuevas
4. **REVISAR** cambios antes de merge a main
5. **MANTENER** `requirements.txt` actualizado

---

**Última actualización**: Diciembre 2024
**Versión del sistema**: 2.0
**Mantenido por**: Equipo de Desarrollo IGAC
