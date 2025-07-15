import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from email_manager import EmailManager
import plotly.express as px
import plotly.graph_objects as go

# Credenciales por proceso
ADMIN_CREDENTIALS = {
    "Almacén": {"usuario": "admin_almacen", "password": "almacen2025"},
    "Apropiaciones": {"usuario": "admin_apropiaciones", "password": "apropiaciones2025"},
    "Contabilidad": {"usuario": "admin_contabilidad", "password": "contabilidad2025"},
    "Gestión Administrativa": {"usuario": "admin_gestion_admin", "password": "gestion2025"},
    "Gestión Documental": {"usuario": "admin_gestion_doc", "password": "documental2025"},
    "Infraestructura": {"usuario": "admin_infraestructura", "password": "infraestructura2025"},
    "Operación Logística": {"usuario": "admin_operacion", "password": "operacion2025"},
    "Presupuesto": {"usuario": "admin_presupuesto", "password": "presupuesto2025"},
    "Seguros y Transporte Especial": {"usuario": "admin_seguros", "password": "seguros2025"},
    "Tesorería": {"usuario": "admin_tesoreria", "password": "tesoreria2025"},
    "Viáticos": {"usuario": "admin_viaticos", "password": "viaticos2025"}
}

def agregar_comentario_admin(comentario_actual, nuevo_comentario, responsable):
    """Add a new admin comment with timestamp and author"""
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M')
    nuevo_entry = f"[{timestamp} - {responsable}]: {nuevo_comentario}"
    
    if comentario_actual and comentario_actual.strip():
        # Append to existing comments
        return f"{comentario_actual}\n\n{nuevo_entry}"
    else:
        # First comment
        return nuevo_entry

def clean_html_content(content):
    """Clean HTML content for display - shared utility function"""
    if not content or not isinstance(content, str):
        return "Sin contenido disponible"
    
    import re
    from html import unescape
    
    # First, decode HTML entities
    content_clean = unescape(content)
    
    # Remove all HTML tags but preserve the text content
    content_clean = re.sub(r'<[^>]+>', '', content_clean)
    
    # Clean up extra whitespace and newlines
    content_clean = re.sub(r'\s+', ' ', content_clean).strip()
    
    # If the result is empty or too short, show fallback
    if not content_clean or len(content_clean.strip()) < 3:
        return "Sin contenido disponible"
    
    return content_clean

def formatear_comentarios_admin_display(comentarios):
    """Format admin comments for display in admin panel"""
    if not comentarios or not comentarios.strip():
        return "Sin comentarios previos"
    
    # Clean HTML content first
    comentarios_clean = clean_html_content(comentarios)
    
    # Split by double newlines (comment separators)
    comentarios_lista = comentarios_clean.split('\n\n')
    comentarios_html = []
    
    for comentario in comentarios_lista:
        if comentario.strip():
            # Parse timestamp and author if available
            if comentario.startswith('[') and ']:' in comentario:
                try:
                    timestamp_autor = comentario.split(']:')[0] + ']'
                    texto = comentario.split(']:')[1].strip()
                    comentarios_html.append(f"**{timestamp_autor}**\n{texto}")
                except:
                    comentarios_html.append(comentario)
            else:
                comentarios_html.append(comentario)
    
    return '\n\n'.join(comentarios_html)

def mostrar_tab_admin(data_manager):
    """Tab principal de administración - SharePoint optimized"""
    
    # Verificar autenticación
    if not st.session_state.get('admin_authenticated', False):
        mostrar_login()
        return
    
    # Obtener proceso del admin autenticado
    proceso_admin = st.session_state.get('admin_proceso', '')
    
    # Header
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.header(f"⚙️ Admin Panel - {proceso_admin}")
    with col2:
        if st.button("🔄 Refresh Data", key="refresh_admin"):
            st.cache_resource.clear()
            st.rerun()
    with col3:
        if st.button("🚪 Cerrar Sesión", key="logout_admin"):
            st.session_state.admin_authenticated = False
            st.session_state.admin_proceso = None
            st.session_state.admin_usuario = None
            st.rerun()
    
    # Auto-refresh data
    data_manager.load_data()
    
    # SharePoint status indicator
    status = data_manager.get_sharepoint_status()
    total_requests = len(data_manager.get_all_requests())
    last_update = datetime.now().strftime('%H:%M:%S')
    
    if status['sharepoint_connected']:
        st.success(f"✅ SharePoint Connected - {total_requests} solicitudes | Actualizado: {last_update}")
    else:
        st.error("❌ SharePoint connection error")
        return
    
    st.markdown("---")
    
    # Obtener datos del proceso
    df = obtener_solicitudes_proceso(data_manager, proceso_admin)
    
    if df.empty:
        st.info(f"📋 No hay solicitudes para {proceso_admin}")
        return
    
    # Mini Dashboard
    mostrar_mini_dashboard(df, proceso_admin)
    
    st.markdown("---")
    
    # Filtros y búsqueda
    mostrar_filtros_busqueda(df)
    
    # Lista de solicitudes para gestionar
    mostrar_lista_solicitudes_admin_improved(data_manager, df, proceso_admin)

def mostrar_login():
    """Formulario de login simple"""
    st.markdown("### 🔐 Acceso de Administrador")
    
    with st.form("admin_login"):
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            proceso = st.selectbox(
                "Proceso:",
                options=list(ADMIN_CREDENTIALS.keys()),
                key="proceso_login"
            )
            
            usuario = st.text_input("Usuario:", key="usuario_login")
            password = st.text_input("Contraseña:", type="password", key="password_login")
            
            submitted = st.form_submit_button("🔓 Iniciar Sesión", use_container_width=True)
            
            if submitted:
                if autenticar_admin(proceso, usuario, password):
                    st.session_state.admin_authenticated = True
                    st.session_state.admin_proceso = proceso
                    st.session_state.admin_usuario = usuario
                    st.success(f"✅ Bienvenido, {usuario}")
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas")
    
    # Mostrar credenciales de prueba
    with st.expander("💡 Credenciales de Prueba"):
        for proceso, creds in ADMIN_CREDENTIALS.items():
            st.write(f"**{proceso}:** `{creds['usuario']}` / `{creds['password']}`")

def autenticar_admin(proceso, usuario, password):
    """Autenticar credenciales"""
    if proceso in ADMIN_CREDENTIALS:
        creds = ADMIN_CREDENTIALS[proceso]
        return usuario == creds["usuario"] and password == creds["password"]
    return False

def obtener_solicitudes_proceso(data_manager, proceso_admin):
    """Obtener solicitudes del proceso específico"""
    df_all = data_manager.get_all_requests()
    
    if df_all.empty:
        return df_all
    
    # Filtrar por proceso
    if 'proceso' in df_all.columns:
        return df_all[df_all['proceso'] == proceso_admin]
    
    # Fallback para datos antiguos
    if 'area' in df_all.columns:
        return df_all[df_all['area'] == proceso_admin]
    
    return pd.DataFrame()

def normalize_datetime(dt):
    """Normalize datetime to timezone-naive for consistent comparisons"""
    if dt is None:
        return None
    
    if hasattr(dt, 'tz_localize'):
        # It's a pandas Timestamp
        if dt.tz is not None:
            return dt.tz_localize(None)
        return dt
    elif hasattr(dt, 'tzinfo'):
        # It's a datetime object
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt
    
    return dt

def mostrar_mini_dashboard(df, proceso):
    """Mini dashboard del proceso - UPDATED with timezone handling"""
    st.subheader(f"📊 Dashboard - {proceso}")
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total = len(df)
        st.metric("📋 Total", total)
    
    with col2:
        asignadas = len(df[df['estado'] == 'Asignada'])
        st.metric("🟡 Asignadas", asignadas)
    
    with col3:
        en_proceso = len(df[df['estado'] == 'En Proceso'])
        st.metric("🔵 En Proceso", en_proceso)
    
    with col4:
        completadas = len(df[df['estado'] == 'Completado'])
        st.metric("✅ Completadas", completadas)
    
    # Alertas
    if asignadas > 0:
        fecha_limite = datetime.now() - timedelta(days=7)
        
        # Normalize datetime columns for comparison
        df_normalized = df.copy()
        if 'fecha_solicitud' in df_normalized.columns:
            df_normalized['fecha_solicitud'] = df_normalized['fecha_solicitud'].apply(normalize_datetime)
            
            # Filter for old pending requests
            antiguas = df_normalized[
                (df_normalized['estado'] == 'Asignada') & 
                (df_normalized['fecha_solicitud'] < fecha_limite)
            ]
            
            if not antiguas.empty:
                st.warning(f"⚠️ {len(antiguas)} solicitudes Asignadas por más de 7 días")
    
    # Gráfico de estados
    if total > 0:
        estados_data = df['estado'].value_counts()
        
        fig = go.Figure(data=[
            go.Pie(
                labels=estados_data.index,
                values=estados_data.values,
                hole=0.4,
                marker=dict(colors=['#FFA726', '#42A5F5', '#66BB6A', '#EF5350'])
            )
        ])
        
        fig.update_layout(
            title="Distribución por Estado",
            height=300,
            showlegend=True,
            margin=dict(t=50, b=0, l=0, r=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)

def mostrar_filtros_busqueda(df):
    """Filtros y búsqueda"""
    st.subheader("🔍 Filtros y Búsqueda")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_estado = st.selectbox(
            "Estado:",
            options=["Todos"] + list(df['estado'].unique()),
            key="filtro_estado"
        )
    
    with col2:
        if 'prioridad' in df.columns:
            filtro_prioridad = st.selectbox(
                "Prioridad:",
                options=["Todas"] + list(df['prioridad'].unique()),
                key="filtro_prioridad"
            )
        else:
            filtro_prioridad = "Todas"
    
    with col3:
        busqueda = st.text_input(
            "Buscar por ID o nombre:",
            placeholder="ID123 o Juan Pérez",
            key="busqueda_admin"
        )
    
    # Aplicar filtros
    df_filtrado = df.copy()
    
    if filtro_estado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['estado'] == filtro_estado]
    
    if filtro_prioridad != "Todas" and 'prioridad' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['prioridad'] == filtro_prioridad]
    
    if busqueda:
        mask = (
            df_filtrado['id_solicitud'].str.contains(busqueda, case=False, na=False) |
            df_filtrado['nombre_solicitante'].str.contains(busqueda, case=False, na=False)
        )
        df_filtrado = df_filtrado[mask]
    
    # Guardar el DataFrame filtrado en session state
    st.session_state.df_filtrado = df_filtrado
    
    st.write(f"📋 Mostrando {len(df_filtrado)} solicitudes")

def mostrar_lista_solicitudes_admin_improved(data_manager, df, proceso):
    """Improved list display with better state management"""
    
    df_filtrado = st.session_state.get('df_filtrado', df)
    
    if df_filtrado.empty:
        st.info("🔍 No se encontraron solicitudes con los filtros aplicados")
        return
    
    st.subheader("📋 Gestionar Solicitudes")
    
    # Sort by priority and date
    if 'prioridad' in df_filtrado.columns:
        orden_prioridad = {'Alta': 0, 'Media': 1, 'Baja': 2, 'Sin asignar': 3}
        df_filtrado = df_filtrado.copy()
        df_filtrado['orden_prioridad'] = df_filtrado['prioridad'].map(orden_prioridad).fillna(3)
        
        if 'fecha_solicitud' in df_filtrado.columns:
            df_filtrado['fecha_solicitud_norm'] = df_filtrado['fecha_solicitud'].apply(normalize_datetime)
            df_filtrado = df_filtrado.sort_values(['orden_prioridad', 'fecha_solicitud_norm'])
        else:
            df_filtrado = df_filtrado.sort_values(['orden_prioridad'])
    
    # Show each request with improved function
    for idx, solicitud in df_filtrado.iterrows():
        mostrar_solicitud_admin_improved(data_manager, solicitud, proceso)
        
def mostrar_solicitud_admin_improved(data_manager, solicitud, proceso):
    """Simplified version with cleaner UI"""
    
    # Determine color and emoji
    prioridad = solicitud.get('prioridad', 'Media')
    estado = solicitud['estado']
    
    if prioridad == 'Alta' and estado == 'Asignada':
        emoji = "🔴"
    elif estado == 'Completado':
        emoji = "✅"
    elif estado == 'En Proceso':
        emoji = "🔵"
    else:
        emoji = "📄"
    
    # Check for recent updates
    recently_updated_key = f'recently_updated_{solicitud["id_solicitud"]}'
    recently_updated = st.session_state.get(recently_updated_key, None)
    
    expanded = False
    show_success = False
    
    if recently_updated:
        time_diff = datetime.now() - recently_updated['timestamp']
        if time_diff.total_seconds() < 30:
            expanded = True
            show_success = True
        else:
            del st.session_state[recently_updated_key]
    
    # Expander title
    titulo = f"{emoji} {solicitud['id_solicitud']} - {solicitud['nombre_solicitante']} ({estado})"
    if prioridad != 'Media':
        titulo += f" - {prioridad}"
    
    with st.expander(titulo, expanded=expanded):
        
        # Show update success message briefly
        if recently_updated and show_success:
            st.success(f"✅ Solicitud Actualizada")
        
        # Basic information
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**📋 Información**")
            st.write(f"**ID:** {solicitud['id_solicitud']}")
            st.write(f"**Solicitante:** {solicitud['nombre_solicitante']}")
            st.write(f"**Email:** {solicitud['email_solicitante']}")
            st.write(f"**Tipo:** {solicitud['tipo_solicitud']}")
            
            if 'territorial' in solicitud and pd.notna(solicitud['territorial']):
                st.write(f"**Territorial:** {solicitud['territorial']}")
            
            if 'fecha_solicitud' in solicitud:
                fecha_solicitud = normalize_datetime(solicitud['fecha_solicitud'])
                if fecha_solicitud:
                    fecha_str = fecha_solicitud.strftime('%d/%m/%Y %H:%M')
                    st.write(f"**Fecha:** {fecha_str}")
        
        with col2:
            st.write("**📝 Descripción**")
            descripcion_limpia = clean_html_content(solicitud.get('descripcion', ''))
            st.text_area(
                "Descripción:",
                value=descripcion_limpia,
                height=100,
                disabled=True,
                key=f"desc_{solicitud['id_solicitud']}"
            )
        
        # Comments history
        st.markdown("---")
        comentarios_actuales = solicitud.get('comentarios_admin', '')
        
        if comentarios_actuales and comentarios_actuales.strip():
            st.markdown("**💬 Historial de Comentarios Administrativos**")
            
            if '[' in comentarios_actuales and ']:' in comentarios_actuales:
                comentarios_formateados = formatear_comentarios_admin_display(comentarios_actuales)
                comentarios_clean = clean_html_content(comentarios_actuales)
                num_comentarios = len([c for c in comentarios_clean.split('\n\n') if c.strip()])
                
                with st.expander(f"Ver {num_comentarios} comentario(s) previo(s)", expanded=False):
                    st.markdown(comentarios_formateados)
            else:
                comentario_limpio = clean_html_content(comentarios_actuales)
                st.info(f"**Comentario previo:** {comentario_limpio}")
        else:
            st.markdown("**💬 Sin comentarios previos**")
        
        # Files section
        st.markdown("---")
        st.markdown("**📎 Archivos**")
        mostrar_archivos_adjuntos_admin(data_manager, solicitud['id_solicitud'])
        
        st.markdown("---")
        
        # Simplified management form
        with st.form(f"manage_{solicitud['id_solicitud']}"):
            
            col1, col2 = st.columns(2)
            
            with col1:
                nuevo_estado = st.selectbox(
                    "Estado:",
                    options=["Asignada", "En Proceso", "Completado", "Cancelado"],
                    index=["Asignada", "En Proceso", "Completado", "Cancelado"].index(solicitud['estado']),
                    key=f"estado_{solicitud['id_solicitud']}"
                )
                
                prioridad_actual = solicitud.get('prioridad', 'Media')
                nueva_prioridad = st.selectbox(
                    "Prioridad:",
                    options=["Sin asignar", "Alta", "Media", "Baja"],
                    index=["Sin asignar", "Alta", "Media", "Baja"].index(prioridad_actual) if prioridad_actual in ["Sin asignar", "Alta", "Media", "Baja"] else 2,
                    key=f"prioridad_{solicitud['id_solicitud']}"
                )
                
                responsable = st.text_input(
                    "Responsable:",
                    value=solicitud.get('responsable_asignado', ''),
                    key=f"responsable_{solicitud['id_solicitud']}"
                )
            
            with col2:
                counter_key = f'comment_counter_{solicitud["id_solicitud"]}'
                comment_counter = st.session_state.get(counter_key, 0)

                nuevo_comentario = st.text_area(
                    "Nuevo comentario:",
                    placeholder="Escriba aquí el nuevo comentario...",
                    height=100,
                    key=f"comentarios_{solicitud['id_solicitud']}_{comment_counter}"
                )
                
                email_responsable = st.text_input(
                    "Email responsable:",
                    placeholder="responsable@igac.gov.co",
                    key=f"email_resp_{solicitud['id_solicitud']}"
                )
            
            # File upload
            new_files = st.file_uploader(
                "Subir archivos:",
                accept_multiple_files=True,
                type=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'jpg', 'jpeg', 'png', 'zip'],
                key=f"admin_files_{solicitud['id_solicitud']}"
            )
            
            # Notification options
            col1, col2 = st.columns(2)
            with col1:
                notificar_solicitante = st.checkbox(
                    "📧 Notificar al solicitante",
                    value=True,
                    key=f"notify_user_{solicitud['id_solicitud']}"
                )
            
            with col2:
                notificar_responsable = st.checkbox(
                    "📧 Notificar al responsable",
                    value=False if not email_responsable else True,
                    key=f"notify_resp_{solicitud['id_solicitud']}"
                )
            
            # Update button
            actualizar = st.form_submit_button(
                "💾 Actualizar",
                type="primary",
                use_container_width=True
            )
            
            # Process update
            if actualizar:
                procesar_actualizacion_sharepoint_simplified(
                    data_manager, solicitud, nuevo_estado, nueva_prioridad, 
                    responsable, email_responsable, nuevo_comentario,
                    notificar_solicitante, notificar_responsable, new_files
                )
                
def mostrar_archivos_adjuntos_admin(data_manager, id_solicitud):
    """Mostrar archivos adjuntos con layout mejorado desde seguimiento - SAFELY"""
    
    try:
        # Get attachments for this request
        attachments = data_manager.get_request_attachments(id_solicitud)
        
        if attachments:
            st.success(f"📁 Se encontraron {len(attachments)} archivo(s) adjunto(s)")
            
            # Display each attachment
            for i, attachment in enumerate(attachments):
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    file_size_mb = attachment['size'] / (1024 * 1024)
                    st.write(f"📄 **{attachment['name']}** ({file_size_mb:.2f} MB)")
                    
                    # Show file creation date if available
                    if attachment.get('created'):
                        try:
                            created_date = datetime.fromisoformat(attachment['created'].replace('Z', '+00:00'))
                            created_str = created_date.strftime('%d/%m/%Y %H:%M')
                            st.caption(f"📅 Subido: {created_str}")
                        except:
                            st.caption("📅 Fecha no disponible")
                    else:
                        st.caption("📅 Fecha no disponible")
                
                with col2:
                    # Download button
                    if attachment.get('download_url'):
                        st.markdown(f"[⬇️ Descargar]({attachment['download_url']})")
                    else:
                        st.info("🔗 Link no disponible")
                
                with col3:
                    # View in browser button for supported file types
                    if attachment.get('web_url'):
                        file_ext = attachment['name'].lower().split('.')[-1] if '.' in attachment['name'] else ''
                        if file_ext in ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'doc', 'docx', 'xls', 'xlsx']:
                            st.markdown(f"[👁️ Ver]({attachment['web_url']})")
                        else:
                            st.info("👁️ No disponible")
                    else:
                        st.info("👁️ No disponible")
                
                # Add separator line between files
                if i < len(attachments) - 1:
                    st.markdown("---")
        else:
            st.info("📭 No hay archivos adjuntos para esta solicitud")
    
    except Exception as e:
        st.warning("⚠️ Error al cargar archivos adjuntos")
        print(f"Error loading attachments for admin: {e}")

def procesar_actualizacion_sharepoint_simplified(data_manager, solicitud, nuevo_estado, nueva_prioridad, 
                                                responsable, email_responsable, nuevo_comentario,
                                                notificar_solicitante, notificar_responsable, new_files=None):
    """Simplified and reliable update process"""
    
    try:
        # Track what actually changed
        changes = {}
        
        # Step 1: Check what changed
        if nuevo_estado != solicitud['estado']:
            changes['estado'] = {'old': solicitud['estado'], 'new': nuevo_estado}
        
        if nueva_prioridad != solicitud.get('prioridad', 'Media'):
            changes['prioridad'] = {'old': solicitud.get('prioridad', 'Media'), 'new': nueva_prioridad}
        
        if responsable and responsable != solicitud.get('responsable_asignado', ''):
            changes['responsable'] = {'old': solicitud.get('responsable_asignado', ''), 'new': responsable}
        
        if nuevo_comentario and nuevo_comentario.strip():
            changes['comentario'] = {'new': nuevo_comentario.strip()}
        
        # Step 2: Prepare comments with automatic status change if needed
        comentarios_actuales = solicitud.get('comentarios_admin', '')
        
        if nuevo_comentario and nuevo_comentario.strip():
            autor = responsable or st.session_state.get('admin_usuario', 'Admin')
            comentarios_finales = agregar_comentario_admin(
                comentarios_actuales, 
                nuevo_comentario.strip(), 
                autor
            )
        else:
            comentarios_finales = comentarios_actuales
            # Add automatic comment for status changes without manual comment
            if 'estado' in changes:
                autor = st.session_state.get('admin_usuario', 'Admin')
                comentario_automatico = f"Estado cambiado de '{changes['estado']['old']}' a '{changes['estado']['new']}'"
                comentarios_finales = agregar_comentario_admin(
                    comentarios_actuales, 
                    comentario_automatico, 
                    f"{autor} (Sistema)"
                )
        
        # Step 3: Update in SharePoint (single transaction)
        with st.spinner("🔄 Actualizando solicitud..."):
            
            # Update priority if changed
            if 'prioridad' in changes:
                success_priority = data_manager.update_request_priority(solicitud['id_solicitud'], nueva_prioridad)
                if not success_priority:
                    st.error("❌ Error al actualizar prioridad")
                    return False
            
            # Update status and comments
            success_status = data_manager.update_request_status(
                solicitud['id_solicitud'],
                nuevo_estado,
                responsable,
                comentarios_finales
            )
            
            if not success_status:
                st.error("❌ Error al actualizar la solicitud")
                return False
            
            # Handle file uploads
            files_uploaded = []
            if new_files:
                for uploaded_file in new_files:
                    if uploaded_file.size <= 10 * 1024 * 1024:  # 10MB limit
                        try:
                            file_data = uploaded_file.read()
                            success = data_manager.upload_attachment_to_item(
                                solicitud['id_solicitud'], file_data, uploaded_file.name
                            )
                            if success:
                                files_uploaded.append(uploaded_file.name)
                        except Exception:
                            continue  # Skip failed uploads
            
            if files_uploaded:
                changes['archivos'] = {'new': files_uploaded}
        
        # Step 4: Send notifications to solicitant only if requested and changes occurred
        email_sent = False
        if notificar_solicitante and changes:
            try:
                email_manager = EmailManager()
                
                solicitud_data = {
                    'id_solicitud': solicitud['id_solicitud'],
                    'tipo_solicitud': solicitud['tipo_solicitud'],
                    'email_solicitante': solicitud['email_solicitante'],
                    'fecha_solicitud': solicitud.get('fecha_solicitud'),
                    'area': solicitud.get('area', 'N/A'),
                    'proceso': solicitud.get('proceso', 'N/A')
                }
                
                # Send notification with only changed fields
                email_sent = email_manager.send_status_update_notification_changes_only(
                    solicitud_data, changes, responsable, email_responsable
                )
                
            except Exception as e:
                print(f"Email notification error: {e}")
        

        # NEW: Step 4b: Optional notification to responsible person
        responsible_email_sent = False
        if notificar_responsable and email_responsable and email_responsable.strip() and changes:
            try:
                responsible_data = {
                    'id_solicitud': solicitud['id_solicitud'],
                    'tipo_solicitud': solicitud['tipo_solicitud'],
                    'email_solicitante': solicitud['email_solicitante'],
                    'nombre_solicitante': solicitud['nombre_solicitante'],
                    'fecha_solicitud': solicitud.get('fecha_solicitud'),
                    'area': solicitud.get('area', 'N/A'),
                    'proceso': solicitud.get('proceso', 'N/A')
                }
                
                responsible_email_sent = email_manager.send_responsible_notification(
                    responsible_data, changes, responsable, email_responsable
                )
                
            except Exception as e:
                print(f"Responsible notification error: {e}")

        # Step 5: Reload data and show success
        data_manager.load_data(force_reload=True)
        
        # Show clean success message
        st.success(f"✅ Solicitud {solicitud['id_solicitud']} actualizada correctamente")
        
        if changes:
            changes_text = []
            if 'estado' in changes:
                changes_text.append(f"Estado: {changes['estado']['new']}")
            if 'prioridad' in changes:
                changes_text.append(f"Prioridad: {changes['prioridad']['new']}")
            if 'responsable' in changes:
                changes_text.append(f"Responsable: {changes['responsable']['new']}")
            if 'comentario' in changes:
                changes_text.append("Nuevo comentario agregado")
            if 'archivos' in changes:
                changes_text.append(f"{len(changes['archivos']['new'])} archivo(s) subido(s)")
            
            if email_sent:
                changes_text.append("Notificación enviada al solicitante")

            if responsible_email_sent:
                changes_text.append(f"Notificación enviada a {email_responsable}")
            
            st.info("🔄 Cambios: " + " | ".join(changes_text))
        
        # Mark for UI feedback
        st.session_state[f'recently_updated_{solicitud["id_solicitud"]}'] = {
            'timestamp': datetime.now(),
            'new_status': nuevo_estado
        }
        
        # INCREMENT COMMENT COUNTER TO FORCE NEW WIDGET
        if nuevo_comentario and nuevo_comentario.strip():
            counter_key = f'comment_counter_{solicitud["id_solicitud"]}'
            current_counter = st.session_state.get(counter_key, 0)
            st.session_state[counter_key] = current_counter + 1
            st.rerun()
        
        return True
            
    except Exception as e:
        st.error(f"❌ Error al procesar actualización: {str(e)}")
        return False
      
def show_update_summary(solicitud, nuevo_estado, nueva_prioridad, responsable, 
                       nuevo_comentario, email_sent, notificar_responsable, email_responsable, files_uploaded=None):
    """Show update summary in a clean way"""
    
    changes_summary = []
    if nuevo_estado != solicitud['estado']:
        changes_summary.append(f"Estado: {solicitud['estado']} → {nuevo_estado}")
    
    if nueva_prioridad != solicitud.get('prioridad', 'Media'):
        changes_summary.append(f"Prioridad: {solicitud.get('prioridad', 'Media')} → {nueva_prioridad}")
    
    if responsable and responsable != solicitud.get('responsable_asignado', ''):
        changes_summary.append(f"Responsable asignado: {responsable}")
    
    if nuevo_comentario and nuevo_comentario.strip():
        changes_summary.append("Nuevo comentario agregado")
    
    if email_sent:
        changes_summary.append("Notificación enviada al solicitante")
    
    if files_uploaded:
        changes_summary.append(f"{len(files_uploaded)} archivo(s) subido(s)")
    
    # Show summary in info box
    with st.container():
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.info(f"""
            **✅ Solicitud {solicitud['id_solicitud']} actualizada**
            
            **Solicitante:** {solicitud['nombre_solicitante']}
            **Nuevo Estado:** {nuevo_estado}
            """)
        
        with col2:
            if changes_summary:
                changes_text = "\n".join([f"• {change}" for change in changes_summary])
                st.success(f"""
                **🔄 Cambios realizados:**
                
                {changes_text}
                """)
            else:
                st.info("• Solicitud actualizada sin cambios")
        
        if notificar_responsable and email_responsable:
            st.info(f"📧 Notificación programada para {email_responsable}")