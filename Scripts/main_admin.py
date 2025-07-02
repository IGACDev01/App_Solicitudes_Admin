import streamlit as st
import pandas as pd
from datetime import datetime
from sharepoint_list_manager import SharePointListManager
from dashboard import mostrar_tab_dashboard
from admin_solicitudes import mostrar_tab_admin

# Single admin credential
ADMIN_CREDENTIAL = {
    "username": "admin",
    "password": "admin2025"
}

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
    .login-container {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 15px;
        border: 1px solid #e9ecef;
        margin: 2rem auto;
        max-width: 400px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .login-header {
        text-align: center;
        color: #495057;
        margin-bottom: 1.5rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
    .sharepoint-status {
        background: #f0f8ff;
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #1f77b4;
        margin-bottom: 20px;
    }
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
    .main .block-container {
        padding-bottom: 60px;
    }
</style>
""", unsafe_allow_html=True)

def show_login():
    """Display login interface"""
    
    # Main title
    st.markdown("""
    <div class="main-header">
        <h1>🔐 Panel de Administración</h1>
        <p>Sistema de Gestión de Solicitudes - IGAC</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Login form
    st.markdown("""
    <div class="login-container">
        <div class="login-header">
            <h2>🔑 Iniciar Sesión</h2>
            <p>Ingrese sus credenciales de administrador</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Center the form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            st.markdown("### 📝 Credenciales")
            
            username = st.text_input(
                "👤 Usuario:",
                placeholder="Ingrese su usuario",
                key="login_username"
            )
            
            password = st.text_input(
                "🔒 Contraseña:",
                type="password",
                placeholder="Ingrese su contraseña",
                key="login_password"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            login_button = st.form_submit_button(
                "🚀 Iniciar Sesión",
                use_container_width=True,
                type="primary"
            )
            
            if login_button:
                if authenticate(username, password):
                    st.session_state.admin_logged_in = True
                    st.session_state.admin_username = username
                    st.success("✅ ¡Bienvenido al panel de administración!")
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas. Intente nuevamente.")
    
    # Show demo credentials
    with st.expander("💡 Credenciales de Demostración", expanded=False):
        st.info(f"**Usuario:** `{ADMIN_CREDENTIAL['username']}`")
        st.info(f"**Contraseña:** `{ADMIN_CREDENTIAL['password']}`")
        st.caption("💡 Estas son las credenciales para acceder al panel de administración")

def authenticate(username, password):
    """Authenticate user credentials"""
    return (username == ADMIN_CREDENTIAL["username"] and 
            password == ADMIN_CREDENTIAL["password"])

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

def show_admin_panel():
    """Show the admin panel after successful login"""
    
    # Header with logout
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.markdown("""
        <div class="main-header">
            <h1>📊 Panel de Administración</h1>
            <p>Sistema de Gestión de Solicitudes - IGAC</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"**👤 Usuario:** {st.session_state.get('admin_username', 'Admin')}")
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Cerrar Sesión", type="secondary", use_container_width=True):
            # Clear session state
            st.session_state.admin_logged_in = False
            st.session_state.admin_username = None
            if 'admin_authenticated' in st.session_state:
                del st.session_state.admin_authenticated
            if 'admin_proceso' in st.session_state:
                del st.session_state.admin_proceso
            if 'admin_usuario' in st.session_state:
                del st.session_state.admin_usuario
            st.rerun()
    
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

    # Show data freshness
    if not cached_df.empty:
        last_update = datetime.now().strftime('%H:%M:%S')
        st.caption(f"📊 Datos en caché | Total solicitudes: {len(cached_df)} | Actualizado: {last_update} | Cache TTL: 60s")
    
    # Create tabs
    tab_titles = [
        "📊 Dashboard",
        "⚙️ Administrar Solicitudes"
    ]
    
    # Create tabs
    tabs = st.tabs(tab_titles)
    
    # Show content based on tab selection  
    with tabs[0]:
        mostrar_tab_dashboard(data_manager)
    
    with tabs[1]:
        mostrar_tab_admin(data_manager)

def main():
    # Check if user is logged in
    if not st.session_state.get('admin_logged_in', False):
        show_login()
    else:
        show_admin_panel()
    
    # Footer
    st.markdown("""
    <div class="footer">
        © 2025 Instituto Geográfico Agustín Codazzi (IGAC) - Todos los derechos reservados | 
        Sistema de Gestión de Solicitudes v1.0
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()