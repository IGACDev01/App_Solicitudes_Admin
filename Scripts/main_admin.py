import streamlit as st
import time
import pandas as pd
from sharepoint_list_manager import GestorListasSharePoint
from shared_timezone_utils import obtener_fecha_actual_colombia
from shared_cache_utils import obtener_cache_key, invalidar_y_actualizar_cache, invalidar_cache_datos, periodic_maintenance

st.set_option('client.showErrorDetails', False)
st.set_option('client.toolbarMode', 'minimal')

# Configuración de página
st.set_page_config(
    page_title="Sistema de Gestión de Solicitudes",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        background: #006AB3;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    .sharepoint-status {
        background: #006AB3;
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #006AB3;
        margin-bottom: 20px;
    }
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #38a962;
        color: white;
        text-align: center;
        padding: 8px 0;
        font-size: 12px;
        z-index: 999;
        box-shadow: 0 -2px 4px rgba(0,0,0,0.1);
    }
    .footer a {
        color: #38a962;
        text-decoration: none;
    }
    .footer a:hover {
        text-decoration: underline;
    }
    /* Agregar margen inferior al contenido principal para evitar superposición con footer */
    .main .block-container {
        padding-bottom: 60px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300, show_spinner=False, max_entries=3)
def obtener_datos_sharepoint_en_cache(cache_key: str = "default"):
    """Obtener datos SharePoint con caché"""
    gestor_datos = obtener_gestor_datos()
    if gestor_datos.df is None or gestor_datos.df.empty:
        gestor_datos.cargar_datos()

    df = gestor_datos.df.copy() if gestor_datos.df is not None else pd.DataFrame()

    # Memory optimization: limit dataframe size if too large
    if len(df) > 1000:
        print(f"⚠️ Large dataset detected ({len(df)} records), optimizing memory usage")
        # Keep only essential columns for UI
        essential_columns = [
            'id_solicitud', 'nombre_solicitante', 'email_solicitante',
            'fecha_solicitud', 'tipo_solicitud', 'estado', 'proceso', 'area'
        ]
        df = df[essential_columns] if all(col in df.columns for col in essential_columns) else df

    return df

@st.cache_resource
def obtener_gestor_datos():
    """Inicializar Gestor de Listas SharePoint y guardarlo en caché"""
    try:
        return GestorListasSharePoint(nombre_lista="Data App Solicitudes")
    except Exception as e:
        st.error(f"Error al inicializar conexión con Lista SharePoint: {e}")
        st.stop()

def inicializar_estado_sesion():
    """Inicializar variables de estado de sesión"""
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
    """Función principal de la aplicación"""

    try:

        # Inicializar estado de sesión
        inicializar_estado_sesion()

        # Perform periodic maintenance
        periodic_maintenance()

        # Título principal
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
            st.empty()

        with col2:
            st.image("Theme/Logo IGAC.png", width=100)

        # Obtener gestor de datos (en caché)
        gestor_datos = obtener_gestor_datos()


        # Llave de cache para forzar la actualización
        cache_key = obtener_cache_key()

        # Obtener datos en caché en lugar de refrescar siempre
        df_en_cache = obtener_datos_sharepoint_en_cache(cache_key)
        gestor_datos.df = df_en_cache

        # Mostrar estado de conexión
        estado = gestor_datos.obtener_estado_sharepoint()
        if not estado['sharepoint_conectado']:
            error_msg = estado.get('error_mensaje', 'Error de conexión desconocido')
            st.error(f"❌ SharePoint: {error_msg}")
            st.info("🔄 Actualizando página en 10 segundos...")
            time.sleep(10)
            st.rerun()

        # Mostrar frescura de datos - actualizado con TTL correcto
        if not df_en_cache.empty:
            ultima_actualizacion = obtener_fecha_actual_colombia().strftime('%H:%M:%S')
            st.caption(f"📊 Datos en caché | Total solicitudes: {len(df_en_cache)} | Actualizado: {ultima_actualizacion} | Cache TTL: 300s")


        # Crear control segmentado para navegación
        tab = st.segmented_control(
            "Navegación",
            ["⚙️ Administrar Solicitudes", "📊 Dashboard"],
            selection_mode="single",
            default="⚙️ Administrar Solicitudes",
            label_visibility="collapsed",
        )

        # Mostrar contenido basado en selección del control segmentado (LAZY LOAD)
        if tab == "⚙️ Administrar Solicitudes":
            from admin_solicitudes import mostrar_tab_administrador
            mostrar_tab_administrador(gestor_datos)

        elif tab == "📊 Dashboard":
            from dashboard import mostrar_tab_dashboard
            mostrar_tab_dashboard(gestor_datos)

        # Footer de la aplicación
        st.markdown("""
        <div class="footer">
            © 2025 Instituto Geográfico Agustín Codazzi (IGAC) - Todos los derechos reservados | 
            Sistema de Gestión de Solicitudes v2.0
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        # Handle JavaScript errors gracefully
        if "dynamically imported module" in str(e):
            st.warning("⚠️ Error de carga temporal. Por favor, recargue la página.")
            if st.button("🔄 Recargar Página"):
                st.rerun()
        else:
            st.error(f"Error: {e}")


if __name__ == "__main__":
    main()