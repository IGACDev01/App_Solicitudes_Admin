import streamlit as st
import pandas as pd
from datetime import datetime
from sharepoint_list_manager import SharePointListManager
from dashboard import mostrar_tab_dashboard
from admin_solicitudes import mostrar_tab_admin

# Page configuration
st.set_page_config(
    page_title="Sistema de Gestión de Solicitudes",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1f77b4, #17becf);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    .sharepoint-status {
        background: #f0f8ff;
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #1f77b4;
        margin-bottom: 20px;
    }
    /* ADD THIS NEW CSS CLASS */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #1f77b4;
        color: white;
        text-align: center;
        padding: 8px 0;
        font-size: 12px;
        z-index: 999;
        box-shadow: 0 -2px 4px rgba(0,0,0,0.1);
    }
    .footer a {
        color: #17becf;
        text-decoration: none;
    }
    .footer a:hover {
        text-decoration: underline;
    }
    /* Add bottom margin to main content to avoid footer overlap */
    .main .block-container {
        padding-bottom: 60px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60)
def get_cached_sharepoint_data():
    """Get SharePoint data with caching"""
    data_manager = get_data_manager()
    data_manager.load_data()
    return data_manager.df.copy() if data_manager.df is not None else pd.DataFrame()

@st.cache_resource
def get_data_manager():
    """Initialize SharePoint List Manager and cache it"""
    try:
        return SharePointListManager(list_name="Data App Solicitudes")
    except Exception as e:
        st.error(f"Failed to initialize SharePoint List connection: {e}")
        st.stop()

def initialize_session_state():
    """Initialize session state variables"""
    if 'dashboard_authenticated' not in st.session_state:
        st.session_state.dashboard_authenticated = False
    if 'dashboard_usuario' not in st.session_state:
        st.session_state.dashboard_usuario = None
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    if 'admin_proceso' not in st.session_state:
        st.session_state.admin_proceso = None
    if 'admin_usuario' not in st.session_state:
        st.session_state.admin_usuario = None

def main():

    # Initialize session state
    initialize_session_state()
    
    # Main title
    st.markdown("""
    <div class="main-header">
        <h1> Sistema de Gestión de Solicitudes</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Get data manager (cached)
    data_manager = get_data_manager()
    
    # Get cached data instead of always refreshing
    cached_df = get_cached_sharepoint_data()
    data_manager.df = cached_df  # Set the cached data
    
    # Show connection status
    status = data_manager.get_sharepoint_status()
    if not status['sharepoint_connected']:
        st.error("❌ SharePoint List connection failed. Please check your configuration.")
        st.stop()

    # Show data freshness - simplified without get_stats()
    if not cached_df.empty:
        last_update = datetime.now().strftime('%H:%M:%S')
        st.caption(f"📊 Datos en caché | Total solicitudes: {len(cached_df)} | Actualizado: {last_update} | Cache TTL: 60s")
    
    
    # Create segmented control for navigation
    tab = st.segmented_control(
        "Navegación",
        ["⚙️ Administrar Solicitudes", "📊 Dashboard"],
        selection_mode="single",
        default="⚙️ Administrar Solicitudes",
        label_visibility="collapsed",
    )
    
    # Show content based on segmented control selection  
    if tab == "⚙️ Administrar Solicitudes":
        mostrar_tab_admin(data_manager)
    
    elif tab == "📊 Dashboard":
        mostrar_tab_dashboard(data_manager)

    st.markdown("""
    <div class="footer">
        © 2025 Instituto Geográfico Agustín Codazzi (IGAC) - Todos los derechos reservados | 
        Sistema de Gestión de Solicitudes v1.0
    </div>
    """, unsafe_allow_html=True)
    

if __name__ == "__main__":
    main()