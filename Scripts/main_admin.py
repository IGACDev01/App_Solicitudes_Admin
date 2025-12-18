"""
Sistema de Gestión de Solicitudes - Aplicación Principal
=========================================================

Punto de entrada principal para el dashboard administrativo del IGAC.
Gestiona la autenticación, caché de datos de SharePoint, y navegación
entre las diferentes pestañas de la aplicación.

Características principales:
- Caché de datos de SharePoint con TTL de 5 minutos (300 segundos)
- Carga lazy de módulos para optimizar rendimiento
- Optimización de memoria para datasets grandes (>1000 registros)
- Mantenimiento periódico de caché y sesión
- Integración con Microsoft Graph API vía SharePoint

Autor: Equipo IGAC
Fecha: 2024-2025
"""

import streamlit as st
import time
import pandas as pd
from sharepoint_list_manager import GestorListasSharePoint
from shared_timezone_utils import obtener_fecha_actual_colombia
from shared_cache_utils import obtener_cache_key, invalidar_y_actualizar_cache, invalidar_cache_datos, periodic_maintenance

# Configuración de opciones de Streamlit para UI limpia
st.set_option('client.showErrorDetails', False)  # Ocultar detalles de error al usuario
st.set_option('client.toolbarMode', 'minimal')   # Toolbar minimalista

# Configuración de página principal
st.set_page_config(
    page_title="Sistema de Gestión de Solicitudes",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS personalizados con marca IGAC
# Colores institucionales: #006AB3 (azul primario), #38a962 (verde footer)
st.markdown("""
<style>
    /* Encabezado principal de la aplicación con color institucional IGAC */
    .main-header {
        background: #006AB3;           /* Azul IGAC */
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }

    /* Indicador de estado de conexión SharePoint */
    .sharepoint-status {
        background: #006AB3;           /* Azul IGAC */
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #006AB3;
        margin-bottom: 20px;
    }

    /* Footer fijo en la parte inferior con información institucional */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #38a962;     /* Verde IGAC */
        color: white;
        text-align: center;
        padding: 8px 0;
        font-size: 12px;
        z-index: 999;
        box-shadow: 0 -2px 4px rgba(0,0,0,0.1);
    }

    /* Estilos para enlaces del footer */
    .footer a {
        color: #38a962;
        text-decoration: none;
    }
    .footer a:hover {
        text-decoration: underline;
    }

    /* Margen inferior al contenido principal para evitar superposición con footer fijo */
    .main .block-container {
        padding-bottom: 60px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300, show_spinner=False, max_entries=3)
def obtener_datos_sharepoint_en_cache(cache_key: str = "default"):
    """
    Obtener datos de SharePoint con sistema de caché optimizado

    Esta función implementa un sistema de caché con TTL (Time To Live) de 5 minutos
    para reducir las llamadas a la API de SharePoint y mejorar el rendimiento.

    Args:
        cache_key (str): Clave de caché que permite forzar actualización cuando cambia.
                        Por defecto "default", pero puede ser timestamp para invalidar.

    Returns:
        pd.DataFrame: DataFrame con datos de solicitudes desde SharePoint.
                     DataFrame vacío si no hay datos disponibles.

    Nota:
        - TTL de 300 segundos (5 minutos) antes de refrescar automáticamente
        - Máximo 3 versiones diferentes en caché (max_entries=3)
        - Optimiza memoria para datasets grandes (>1000 registros)
        - Para invalidar manualmente: usar invalidar_cache_datos() y cambiar cache_key
    """
    gestor_datos = obtener_gestor_datos()

    # Cargar datos si el gestor no tiene datos cargados
    if gestor_datos.df is None or gestor_datos.df.empty:
        gestor_datos.cargar_datos()

    # Crear copia para evitar modificaciones al DataFrame original
    df = gestor_datos.df.copy() if gestor_datos.df is not None else pd.DataFrame()

    # Optimización de memoria para datasets grandes
    # Si hay más de 1000 registros, limitar a columnas esenciales para reducir uso de RAM
    if len(df) > 1000:
        print(f"⚠️ Dataset grande detectado ({len(df)} registros), optimizando uso de memoria")

        # Mantener solo columnas esenciales para la UI
        essential_columns = [
            'id_solicitud', 'nombre_solicitante', 'email_solicitante',
            'fecha_solicitud', 'tipo_solicitud', 'estado', 'proceso', 'area'
        ]

        # Aplicar filtro solo si todas las columnas esenciales existen
        if all(col in df.columns for col in essential_columns):
            df = df[essential_columns]

    return df


@st.cache_resource
def obtener_gestor_datos():
    """
    Inicializar Gestor de Listas SharePoint y mantenerlo en caché de recursos

    Esta función crea una instancia única del gestor de SharePoint que se reutiliza
    durante toda la sesión de Streamlit. Se usa @st.cache_resource (no @st.cache_data)
    porque GestorListasSharePoint mantiene estado y conexiones.

    Returns:
        GestorListasSharePoint: Instancia única del gestor conectado a SharePoint

    Raises:
        Exception: Si falla la inicialización, detiene la aplicación con st.stop()

    Nota:
        - Esta función se ejecuta UNA SOLA VEZ por sesión de Streamlit
        - El gestor mantiene tokens de autenticación y estado de conexión
        - Si hay errores de conexión, la aplicación se detiene completamente
    """
    try:
        return GestorListasSharePoint(nombre_lista="Data App Solicitudes")
    except Exception as e:
        st.error(f"❌ Error al inicializar conexión con SharePoint: {e}")
        st.error("🔍 Verifique credenciales en .streamlit/secrets.toml")
        st.stop()

def inicializar_estado_sesion():
    """
    Inicializar variables de estado de sesión de Streamlit

    Establece valores por defecto para todas las variables de autenticación y estado
    que se mantienen durante la sesión del usuario. Estas variables persisten mientras
    el usuario esté navegando la aplicación.

    Variables de estado inicializadas:
        - dashboard_autenticado (bool): Si el usuario está autenticado en el dashboard
        - usuario_dashboard (str): Nombre de usuario autenticado en dashboard
        - admin_autenticado (bool): Si el administrador está autenticado
        - area_admin (str): Área del administrador autenticado
        - proceso_admin (str): Proceso/departamento del administrador
        - usuario_admin (str): Email del administrador autenticado

    Nota:
        Esta función es idempotente - puede llamarse múltiples veces sin efectos adversos.
        Solo inicializa variables que no existen en st.session_state.
    """
    if 'dashboard_autenticado' not in st.session_state:
        st.session_state.dashboard_autenticado = False

    if 'usuario_dashboard' not in st.session_state:
        st.session_state.usuario_dashboard = None

    if 'admin_autenticado' not in st.session_state:
        st.session_state.admin_autenticado = False

    if 'area_admin' not in st.session_state:
        st.session_state.area_admin = None

    if 'proceso_admin' not in st.session_state:
        st.session_state.proceso_admin = None

    if 'usuario_admin' not in st.session_state:
        st.session_state.usuario_admin = None


def main():
    """
    Función principal de la aplicación Streamlit

    Orquesta todo el flujo de la aplicación:
    1. Inicialización de estado de sesión
    2. Mantenimiento periódico de caché
    3. Carga de datos de SharePoint (con caché)
    4. Verificación de estado de conexión
    5. Navegación entre pestañas (lazy loading)
    6. Renderizado de UI con estilos IGAC

    Nota:
        - Usa lazy loading para módulos de pestañas (solo importa cuando se necesita)
        - Implementa auto-refresh si hay errores de conexión SharePoint
        - Maneja errores de JavaScript/importación dinámica gracefully
    """
    try:
        # 1. Inicializar estado de sesión con valores por defecto
        inicializar_estado_sesion()

        # 2. Ejecutar mantenimiento periódico de caché y limpieza de sesión
        periodic_maintenance()

        # 3. Renderizar encabezado con logo IGAC
        # Layout: 10 partes título, 0.5 espaciador, 1 parte logo
        col1, spacer, col2 = st.columns([10, 0.5, 1])

        with col1:
            st.markdown("""
            <div class="main-header">
                <div class="header-text">
                    <h1>Administrador de Solicitudes</h1>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with spacer:
            st.empty()  # Espaciador visual entre título y logo

        with col2:
            st.image("Theme/Logo IGAC.png", width=100)

        # 4. Obtener gestor de datos (singleton en caché de recursos)
        gestor_datos = obtener_gestor_datos()

        # 5. Obtener clave de caché actual (permite invalidación manual)
        # Si se llama invalidar_y_actualizar_cache(), esta clave cambiará
        cache_key = obtener_cache_key()

        # 6. Cargar datos usando sistema de caché con TTL de 5 minutos
        # El parámetro cache_key permite forzar refresh cuando cambia
        df_en_cache = obtener_datos_sharepoint_en_cache(cache_key)
        gestor_datos.df = df_en_cache  # Actualizar DataFrame en gestor

        # 7. Verificar estado de conexión con SharePoint
        estado = gestor_datos.obtener_estado_sharepoint()
        if not estado['sharepoint_conectado']:
            # Si no hay conexión, mostrar error y auto-refrescar cada 10 segundos
            error_msg = estado.get('error_mensaje', 'Error de conexión desconocido')
            st.error(f"❌ SharePoint: {error_msg}")
            st.info("🔄 Actualizando página en 10 segundos...")
            time.sleep(10)
            st.rerun()

        # 8. Mostrar información de caché y estado de datos
        if not df_en_cache.empty:
            ultima_actualizacion = obtener_fecha_actual_colombia().strftime('%H:%M:%S')
            st.caption(
                f"📊 Datos en caché | "
                f"Total solicitudes: {len(df_en_cache)} | "
                f"Actualizado: {ultima_actualizacion} | "
                f"Cache TTL: 300s"
            )

        # 9. Control de navegación segmentado (pestañas modernas de Streamlit)
        tab = st.segmented_control(
            "Navegación",
            ["⚙️ Administrar Solicitudes", "📊 Dashboard"],
            selection_mode="single",
            default="⚙️ Administrar Solicitudes",
            label_visibility="collapsed",
        )

        # 10. Carga lazy de módulos según pestaña seleccionada
        # IMPORTANTE: Los imports se hacen DENTRO del if para cargar solo lo necesario
        # Esto mejora el tiempo de carga inicial de la aplicación
        if tab == "⚙️ Administrar Solicitudes":
            from admin_solicitudes import mostrar_tab_administrador
            mostrar_tab_administrador(gestor_datos)

        elif tab == "📊 Dashboard":
            from dashboard import mostrar_tab_dashboard
            mostrar_tab_dashboard(gestor_datos)

        # 11. Footer institucional fijo en la parte inferior
        st.markdown("""
        <div class="footer">
            © 2025 Instituto Geográfico Agustín Codazzi (IGAC) - Todos los derechos reservados |
            Sistema de Gestión de Solicitudes v2.0
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        # Manejo de errores específicos de Streamlit
        if "dynamically imported module" in str(e):
            # Error común cuando Streamlit recarga módulos dinámicamente
            # Solución: ofrecer botón de recarga manual
            st.warning("⚠️ Error de carga temporal. Por favor, recargue la página.")
            if st.button("🔄 Recargar Página"):
                st.rerun()
        else:
            # Otros errores: mostrar al usuario y registrar en consola
            st.error(f"❌ Error inesperado: {e}")
            print(f"Error en main(): {e}")


# Punto de entrada de la aplicación
# Ejecutar: streamlit run Scripts/main_admin.py
if __name__ == "__main__":
    main()