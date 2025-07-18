import streamlit as st
import pandas as pd
from sharepoint_list_manager import GestorListasSharePoint
from dashboard import mostrar_tab_dashboard
from timezone_utils_admin import obtener_fecha_actual_colombia
from admin_solicitudes import mostrar_tab_administrador

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

@st.cache_data(ttl=60)
def obtener_datos_sharepoint_en_cache():
    """Obtener datos SharePoint con caché"""
    gestor_datos = obtener_gestor_datos()
    gestor_datos.cargar_datos()
    return gestor_datos.df.copy() if gestor_datos.df is not None else pd.DataFrame()

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
    if 'proceso_admin' not in st.session_state:
        st.session_state.proceso_admin = None
    if 'usuario_admin' not in st.session_state:
        st.session_state.usuario_admin = None

def main():
    """Función principal de la aplicación"""

    # Inicializar estado de sesión
    inicializar_estado_sesion()
    
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
    
    # Obtener datos en caché en lugar de refrescar siempre
    df_en_cache = obtener_datos_sharepoint_en_cache()
    gestor_datos.df = df_en_cache  # Establecer los datos en caché
    
    # Mostrar estado de conexión
    estado = gestor_datos.obtener_estado_sharepoint()
    if not estado['sharepoint_conectado']:
        st.error("❌ Falló conexión con Lista SharePoint. Por favor verifique su configuración.")
        st.stop()

    # Mostrar frescura de datos - simplificado sin get_stats()
    if not df_en_cache.empty:
        ultima_actualizacion = obtener_fecha_actual_colombia().strftime('%H:%M:%S')
        st.caption(f"📊 Datos en caché | Total solicitudes: {len(df_en_cache)} | Actualizado: {ultima_actualizacion} | Cache TTL: 60s")
    
    
    # Crear control segmentado para navegación
    tab = st.segmented_control(
        "Navegación",
        ["⚙️ Administrar Solicitudes", "📊 Dashboard"],
        selection_mode="single",
        default="⚙️ Administrar Solicitudes",
        label_visibility="collapsed",
    )
    
    # Mostrar contenido basado en selección del control segmentado  
    if tab == "⚙️ Administrar Solicitudes":
        mostrar_tab_administrador(gestor_datos)
    
    elif tab == "📊 Dashboard":
        mostrar_tab_dashboard(gestor_datos)

    # Footer de la aplicación
    st.markdown("""
    <div class="footer">
        © 2025 Instituto Geográfico Agustín Codazzi (IGAC) - Todos los derechos reservados | 
        Sistema de Gestión de Solicitudes v2.0
    </div>
    """, unsafe_allow_html=True)
    

if __name__ == "__main__":
    main()