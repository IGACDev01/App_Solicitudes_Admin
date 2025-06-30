import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from email_manager import EmailManager
import plotly.express as px
import plotly.graph_objects as go
import time

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

def formatear_comentarios_admin_display(comentarios):
    """Format admin comments for display in admin panel"""
    if not comentarios or not comentarios.strip():
        return "Sin comentarios previos"
    
    # Split by double newlines (comment separators)
    comentarios_lista = comentarios.split('\n\n')
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
    mostrar_lista_solicitudes_admin(data_manager, df, proceso_admin)

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

def mostrar_mini_dashboard(df, proceso):
    """Mini dashboard del proceso"""
    st.subheader(f"📊 Dashboard - {proceso}")
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total = len(df)
        st.metric("📋 Total", total)
    
    with col2:
        pendientes = len(df[df['estado'] == 'Pendiente'])
        st.metric("🟡 Pendientes", pendientes)
    
    with col3:
        en_proceso = len(df[df['estado'] == 'En Proceso'])
        st.metric("🔵 En Proceso", en_proceso)
    
    with col4:
        completadas = len(df[df['estado'] == 'Completado'])
        st.metric("✅ Completadas", completadas)
    
    # Alertas
    if pendientes > 0:
        fecha_limite = datetime.now() - timedelta(days=7)
        antiguas = df[(df['estado'] == 'Pendiente') & (df['fecha_solicitud'] < fecha_limite)]
        
        if not antiguas.empty:
            st.warning(f"⚠️ {len(antiguas)} solicitudes pendientes por más de 7 días")
    
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

def mostrar_lista_solicitudes_admin(data_manager, df, proceso):
    """Lista de solicitudes para administrar - SharePoint optimized"""
    
    # Obtener DataFrame filtrado
    df_filtrado = st.session_state.get('df_filtrado', df)
    
    if df_filtrado.empty:
        st.info("🔍 No se encontraron solicitudes con los filtros aplicados")
        return
    
    st.subheader("📋 Gestionar Solicitudes")
    
    # Ordenar por prioridad y fecha
    if 'prioridad' in df_filtrado.columns:
        orden_prioridad = {'Alta': 0, 'Media': 1, 'Baja': 2}
        df_filtrado['orden_prioridad'] = df_filtrado['prioridad'].map(orden_prioridad)
        df_filtrado = df_filtrado.sort_values(['orden_prioridad', 'fecha_solicitud'])
    
    # Mostrar cada solicitud
    for idx, solicitud in df_filtrado.iterrows():
        mostrar_solicitud_admin(data_manager, solicitud, proceso)

def mostrar_solicitud_admin(data_manager, solicitud, proceso):
    """Mostrar una solicitud individual para administrar - UPDATED with enhanced comments"""
    
    # Determinar color y emoji según estado y prioridad
    prioridad = solicitud.get('prioridad', 'Media')
    estado = solicitud['estado']
    
    if prioridad == 'Alta' and estado == 'Pendiente':
        emoji = "🔴"
    elif estado == 'Completado':
        emoji = "✅"
    elif estado == 'En Proceso':
        emoji = "🔵"
    else:
        emoji = "📄"
    
    # Título del expander
    titulo = f"{emoji} {solicitud['id_solicitud']} - {solicitud['nombre_solicitante']} ({estado})"
    if prioridad != 'Media':
        titulo += f" - {prioridad}"
    
    with st.expander(titulo):
        # Información de la solicitud
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
                fecha_str = solicitud['fecha_solicitud'].strftime('%d/%m/%Y %H:%M')
                st.write(f"**Fecha:** {fecha_str}")
        
        with col2:
            st.write("**📝 Descripción**")
            st.text_area(
                "Descripción:",
                value=solicitud.get('descripcion', ''),
                height=100,
                disabled=True,
                key=f"desc_{solicitud['id_solicitud']}"
            )
        
        # ENHANCED: Display comment history
        st.markdown("---")
        comentarios_actuales = solicitud.get('comentarios_admin', '')
        
        if comentarios_actuales and comentarios_actuales.strip():
            st.markdown("**💬 Historial de Comentarios Administrativos**")
            
            # Check if there are multiple timestamped comments
            if '[' in comentarios_actuales and ']:' in comentarios_actuales:
                comentarios_formateados = formatear_comentarios_admin_display(comentarios_actuales)
                num_comentarios = len([c for c in comentarios_actuales.split('\n\n') if c.strip()])
                
                with st.expander(f"Ver {num_comentarios} comentario(s) previo(s)", expanded=False):
                    st.markdown(comentarios_formateados)
            else:
                # Single old comment
                st.info(f"**Comentario previo:** {comentarios_actuales}")
        else:
            st.markdown("**💬 Comentarios Administrativos**")
            st.info("Sin comentarios previos")
        
        # File management section
        st.markdown("---")
        st.markdown("**📎 Archivos de la Solicitud**")
        
        col_files1, col_files2 = st.columns(2)
        
        with col_files1:
            # Show existing files
            existing_files = data_manager.get_request_attachments(solicitud['id_solicitud'])
            
            if existing_files:
                st.write("📁 **Archivos existentes:**")
                for file_info in existing_files:
                    file_size_mb = file_info['size'] / (1024 * 1024)
                    col_file1, col_file2 = st.columns([3, 1])
                    with col_file1:
                        st.write(f"• {file_info['name']} ({file_size_mb:.1f}MB)")
                    with col_file2:
                        if st.button("💾", key=f"download_{file_info['id']}", help="Descargar archivo"):
                            if file_info.get('download_url'):
                                st.markdown(f"[⬇️ Descargar]({file_info['download_url']})")
                            else:
                                st.info("URL de descarga no disponible")
            else:
                st.info("📁 No hay archivos adjuntos")
        
        with col_files2:
            st.write("📤 **Subir nuevos archivos**")
            st.caption("Use el formulario de abajo para subir archivos")
        
        st.markdown("---")
        
        # Formulario de gestión - UPDATED with enhanced comment handling
        with st.form(f"manage_{solicitud['id_solicitud']}"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Estado
                nuevo_estado = st.selectbox(
                    "Estado:",
                    options=["Pendiente", "En Proceso", "Completado", "Cancelado"],
                    index=["Pendiente", "En Proceso", "Completado", "Cancelado"].index(solicitud['estado']),
                    key=f"estado_{solicitud['id_solicitud']}"
                )
                
                # Prioridad
                prioridad_actual = solicitud.get('prioridad', 'Media')
                nueva_prioridad = st.selectbox(
                    "Prioridad:",
                    options=["Sin asignar", "Alta", "Media", "Baja"],
                    index=["Sin asignar", "Alta", "Media", "Baja"].index(prioridad_actual) if prioridad_actual in ["Sin asignar", "Alta", "Media", "Baja"] else 0,
                    key=f"prioridad_{solicitud['id_solicitud']}"
                )
            
            with col2:
                # Responsable
                responsable = st.text_input(
                    "Responsable:",
                    value=solicitud.get('responsable_asignado', ''),
                    key=f"responsable_{solicitud['id_solicitud']}"
                )
                
                # Email del responsable
                email_responsable = st.text_input(
                    "Email responsable:",
                    value="",
                    placeholder="responsable@igac.gov.co",
                    key=f"email_resp_{solicitud['id_solicitud']}"
                )
            
            with col3:
                # ENHANCED: Nuevo comentario (será agregado al historial)
                nuevo_comentario = st.text_area(
                    "Agregar nuevo comentario:",
                    placeholder="Escriba aquí el nuevo comentario que será agregado al historial...",
                    height=100,
                    key=f"comentarios_{solicitud['id_solicitud']}",
                    help="Este comentario se agregará al historial con fecha y hora automáticas"
                )
            
            # File upload section in form
            st.markdown("**📎 Subir Archivos Adicionales**")
            new_files = st.file_uploader(
                "Seleccionar archivos para subir:",
                accept_multiple_files=True,
                type=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'jpg', 'jpeg', 'png', 'zip'],
                help="Máximo 10MB por archivo. Se guardarán como attachments en SharePoint.",
                key=f"admin_files_{solicitud['id_solicitud']}"
            )
            
            if new_files:
                st.info(f"📎 {len(new_files)} archivo(s) seleccionado(s) para subir")
                for file in new_files:
                    file_size_mb = file.size / (1024 * 1024)
                    if file_size_mb > 10:
                        st.error(f"❌ {file.name} es muy grande ({file_size_mb:.1f}MB)")
                    else:
                        st.success(f"✅ {file.name} ({file_size_mb:.1f}MB)")
            
            # Opciones de notificación
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
                    value=False,
                    key=f"notify_resp_{solicitud['id_solicitud']}"
                )
            
            # Botón de actualización
            actualizar = st.form_submit_button(
                "💾 Actualizar y Guardar en SharePoint",
                type="primary",
                use_container_width=True
            )
            
            # Procesar actualización
            if actualizar:
                procesar_actualizacion_sharepoint_enhanced(
                    data_manager, solicitud, nuevo_estado, nueva_prioridad, 
                    responsable, email_responsable, nuevo_comentario,
                    notificar_solicitante, notificar_responsable, new_files
                )

def procesar_actualizacion_sharepoint_enhanced(data_manager, solicitud, nuevo_estado, nueva_prioridad, 
                                             responsable, email_responsable, nuevo_comentario,
                                             notificar_solicitante, notificar_responsable, new_files=None):
    """Procesar la actualización de una solicitud - ENHANCED with comment history"""
    
    try:
        with st.spinner("Actualizando en SharePoint..."):
            # Get current admin comments
            comentarios_actuales = solicitud.get('comentarios_admin', '')
            
            # Add new comment if provided
            if nuevo_comentario and nuevo_comentario.strip():
                autor = responsable or st.session_state.get('admin_usuario', 'Admin')
                comentarios_finales = agregar_comentario_admin(
                    comentarios_actuales, 
                    nuevo_comentario.strip(), 
                    autor
                )
                st.info(f"💬 Se agregará nuevo comentario al historial")
            else:
                comentarios_finales = comentarios_actuales
                if nuevo_estado != solicitud['estado'] and not nuevo_comentario:
                    # Add automatic system comment for status changes
                    autor = st.session_state.get('admin_usuario', 'Admin')
                    comentario_automatico = f"Estado cambiado de '{solicitud['estado']}' a '{nuevo_estado}'"
                    comentarios_finales = agregar_comentario_admin(
                        comentarios_actuales, 
                        comentario_automatico, 
                        f"{autor} (Sistema)"
                    )
            
            # Update priority if changed
            if nueva_prioridad != solicitud.get('prioridad', 'Media'):
                success_priority = data_manager.update_request_priority(solicitud['id_solicitud'], nueva_prioridad)
                if not success_priority:
                    st.error("❌ Error al actualizar prioridad")
                    return
            
            # Update status and comments
            success_status = data_manager.update_request_status(
                solicitud['id_solicitud'],
                nuevo_estado,
                responsable,
                comentarios_finales  # Use the enhanced comments
            )
            
            if success_status:
                # Handle file uploads
                files_uploaded = []
                if new_files:
                    with st.spinner(f"Subiendo {len(new_files)} archivo(s)..."):
                        for uploaded_file in new_files:
                            if uploaded_file.size <= 10 * 1024 * 1024:  # 10MB limit
                                file_data = uploaded_file.read()
                                success = data_manager.upload_attachment_to_item(
                                    solicitud['id_solicitud'], file_data, uploaded_file.name
                                )
                                
                                if success:
                                    files_uploaded.append(uploaded_file.name)
                
                # Reload data to reflect changes
                data_manager.load_data(force_reload=True)
                
                st.success("✅ Solicitud actualizada con comentario registrado en el historial")
                
                # Send notifications
                if notificar_solicitante:
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
                        
                        # Send only the new comment to user, not all comment history
                        comentario_para_usuario = nuevo_comentario.strip() if nuevo_comentario and nuevo_comentario.strip() else f"Estado actualizado a: {nuevo_estado}"
                        if files_uploaded:
                            comentario_para_usuario += f"\n\nArchivos adjuntos: {', '.join(files_uploaded)}"
                        
                        email_sent = email_manager.send_status_update_notification(
                            solicitud_data, nuevo_estado, comentario_para_usuario
                        )
                        
                        if email_sent:
                            st.success("📧 Notificación enviada al solicitante")
                    except Exception as e:
                        st.warning(f"⚠️ Error enviando notificación: {e}")
                
                if notificar_responsable and email_responsable:
                    st.success(f"📧 Notificación programada para {email_responsable}")
                
                if files_uploaded:
                    st.success(f"📎 {len(files_uploaded)} archivo(s) subidos exitosamente")
                
                # Clear cache to force refresh
                st.cache_resource.clear()
                
                # Auto-refresh after 2 seconds
                time.sleep(2)
                st.rerun()
                    
            else:
                st.error("❌ Error al actualizar la solicitud")
                
    except Exception as e:
        st.error(f"❌ Error al procesar actualización: {str(e)}")