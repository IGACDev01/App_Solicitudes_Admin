import streamlit as st
import time
import pandas as pd
from sharepoint_list_manager import GestorListasSharePoint
from timezone_utils_admin import obtener_fecha_actual_colombia
from utils import obtener_cache_key

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


def invalidar_cache_datos():
    """Invalidar cache de datos después de operaciones de escritura"""
    try:
        # Clear the specific cache function
        obtener_datos_sharepoint_en_cache.clear()
        print("✅ Cache de datos invalidado")
    except Exception as e:
        print(f"⚠️ Error invalidando cache: {e}")

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


def cleanup_streamlit_cache():
    """Clean up Streamlit cache periodically"""
    try:
        # Try to clear cache if it exists
        # Note: get_stats() may not be available in all Streamlit versions
        try:
            cache_info = st.cache_data.get_stats()
            total_entries = sum(len(entries) for entries in cache_info.values())

            if total_entries > 20:  # If too many cached items
                print(f"🧹 Cleaning cache: {total_entries} entries found")
                st.cache_data.clear()
                print("✅ Cache cleared")
        except AttributeError:
            # get_stats() not available, skip detailed cleanup
            pass

    except Exception as e:
        print(f"⚠️ Cache cleanup error: {e}")


def cleanup_old_session_data():
    """Clean up old session state data"""
    try:
        keys_to_remove = []

        # Clean up old form IDs (keep only recent ones)
        for key in st.session_state.keys():
            if key.startswith('old_form_ids') and len(st.session_state.get(key, [])) > 10:
                # Keep only last 5 form IDs
                st.session_state[key] = st.session_state[key][-5:]

            # Remove temporary flags older than 1 hour
            if key.startswith('temp_') or key.startswith('just_submitted_'):
                keys_to_remove.append(key)

        # Remove old temporary keys
        for key in keys_to_remove:
            try:
                del st.session_state[key]
            except:
                pass

        if keys_to_remove:
            print(f"🧹 Cleaned up {len(keys_to_remove)} old session keys")

    except Exception as e:
        print(f"⚠️ Session cleanup error: {e}")


def periodic_maintenance():
    """Perform periodic maintenance tasks"""
    # Only run maintenance occasionally
    if 'last_maintenance' not in st.session_state:
        st.session_state.last_maintenance = 0

    current_time = time.time()

    # Run maintenance every 30 minutes
    if current_time - st.session_state.last_maintenance > 1800:  # 30 minutes
        print("🔧 Running periodic maintenance...")

        # Clean up old session state data
        cleanup_old_session_data()

        # Clean up cache if needed
        cleanup_streamlit_cache()

        # Update maintenance timestamp
        st.session_state.last_maintenance = current_time
        print("✅ Maintenance completed")

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