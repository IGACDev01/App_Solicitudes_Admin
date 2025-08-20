import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from email_manager import GestorNotificacionesEmail
import plotly.graph_objects as go
from timezone_utils_admin import obtener_fecha_actual_colombia, convertir_a_colombia, formatear_fecha_colombia
from utils import invalidar_y_actualizar_cache

# Credenciales por proceso
CREDENCIALES_ADMINISTRADORES = {
    "Almacén": {"usuario": "admin_almacen", "password": "almacen2025"},
    "Apropiaciones": {"usuario": "admin_apropiaciones", "password": "apropiaciones2025"},
    "Contabilidad": {"usuario": "admin_contabilidad", "password": "contabilidad2025"},
    "Gestión Administrativa": {"usuario": "admin_gestion_admin", "password": "gestion2025"},
    "Gestión Documental": {"usuario": "admin_gestion_doc", "password": "documental2025"},
    "Infraestructura": {"usuario": "admin_infraestructura", "password": "infraestructura2025"},
    "Operación Logística SAF": {"usuario": "admin_operacion", "password": "operacion2025"},
    "Presupuesto": {"usuario": "admin_presupuesto", "password": "presupuesto2025"},
    "Seguros y Transporte Especial": {"usuario": "admin_seguros", "password": "seguros2025"},
    "Tesorería": {"usuario": "admin_tesoreria", "password": "tesoreria2025"},
    "Viáticos": {"usuario": "admin_viaticos", "password": "viaticos2025"}
}

def agregar_comentario_administrador(comentario_actual, nuevo_comentario, responsable):
    """Agregar un nuevo comentario administrativo con timestamp y autor"""
    timestamp = obtener_fecha_actual_colombia().strftime('%d/%m/%Y %H:%M COT')
    nueva_entrada = f"[{timestamp} - {responsable}]: {nuevo_comentario}"
    
    if comentario_actual and comentario_actual.strip():
        # Agregar a comentarios existentes
        return f"{comentario_actual}\n\n{nueva_entrada}"
    else:
        # Primer comentario
        return nueva_entrada

def limpiar_contenido_html(contenido):
    """Limpiar contenido HTML para visualización - función de utilidad compartida"""
    if not contenido or not isinstance(contenido, str):
        return "Sin contenido disponible"
    
    import re
    from html import unescape
    
    # Primero, decodificar entidades HTML
    contenido_limpio = unescape(contenido)
    
    # Remover todas las etiquetas HTML pero preservar el contenido de texto
    contenido_limpio = re.sub(r'<[^>]+>', '', contenido_limpio)
    
    # Limpiar espacios en blanco extra y saltos de línea
    contenido_limpio = re.sub(r'\s+', ' ', contenido_limpio).strip()
    
    # Si el resultado está vacío o muy corto, mostrar fallback
    if not contenido_limpio or len(contenido_limpio.strip()) < 3:
        return "Sin contenido disponible"
    
    return contenido_limpio

def formatear_comentarios_administrador_para_mostrar(comentarios):
    """Formatear comentarios administrativos para visualización en panel de administración"""
    if not comentarios or not comentarios.strip():
        return "Sin comentarios previos"
    
    # Limpiar contenido HTML primero
    comentarios_limpios = limpiar_contenido_html(comentarios)
    
    # Dividir por dobles saltos de línea (separadores de comentarios)
    lista_comentarios = comentarios_limpios.split('\n\n')
    comentarios_html = []
    
    for comentario in lista_comentarios:
        if comentario.strip():
            # Parsear timestamp y autor si están disponibles
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

def mostrar_tab_administrador(gestor_datos):
    """Tab principal de administración - optimizado para SharePoint"""
    
    # Verificar autenticación
    if not st.session_state.get('admin_autenticado', False):
        mostrar_login_administrador()
        return
    
    # Obtener proceso del admin autenticado
    proceso_admin = st.session_state.get('proceso_admin', '')
    
    # Header
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.header(f"⚙️ Panel de Administración - {proceso_admin}")
    with col2:
        if st.button("🔄 Actualizar Datos", key="actualizar_admin"):
            invalidar_y_actualizar_cache()
            st.cache_resource.clear()
            st.rerun()
    with col3:
        if st.button("🚪 Cerrar Sesión", key="cerrar_sesion_admin"):
            st.session_state.admin_autenticado = False
            st.session_state.proceso_admin = None
            st.session_state.usuario_admin = None
            st.rerun()
    
    # Auto-actualizar datos
    gestor_datos.cargar_datos()
    
    # Indicador de estado de SharePoint
    estado = gestor_datos.obtener_estado_sharepoint()
    total_solicitudes = len(gestor_datos.obtener_todas_solicitudes())
    ultima_actualizacion = obtener_fecha_actual_colombia().strftime('%H:%M:%S')
    
    if estado['sharepoint_conectado']:
        st.success(f"✅ Conectado - Última Actualización: {ultima_actualizacion}")
    else:
        st.error("❌ Error de conexión SharePoint")
        return
    
    st.markdown("---")
    
    # Obtener datos del proceso
    df = obtener_solicitudes_del_proceso(gestor_datos, proceso_admin)
    
    if df.empty:
        st.info(f"📋 No hay solicitudes para {proceso_admin}")
        return
    
    # Mini Dashboard
    mostrar_mini_dashboard(df, proceso_admin)
    
    st.markdown("---")
    
    # Filtros y búsqueda
    mostrar_filtros_busqueda(df)
    
    # Lista de solicitudes para gestionar
    mostrar_lista_solicitudes_administrador_mejorada(gestor_datos, df, proceso_admin)

def mostrar_login_administrador():
    """Formulario de login simple"""
    st.markdown("### 🔐 Acceso de Administrador")
    
    with st.form("login_admin"):
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            proceso = st.selectbox(
                "Proceso:",
                options=list(CREDENCIALES_ADMINISTRADORES.keys()),
                key="proceso_login"
            )
            
            usuario = st.text_input("Usuario:", key="usuario_login")
            password = st.text_input("Contraseña:", type="password", key="password_login")
            
            submitted = st.form_submit_button("🔓 Iniciar Sesión", use_container_width=True)
            
            if submitted:
                if autenticar_administrador(proceso, usuario, password):
                    st.session_state.admin_autenticado = True
                    st.session_state.proceso_admin = proceso
                    st.session_state.usuario_admin = usuario
                    st.success(f"✅ Bienvenido, {usuario}")
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas")
    
    # Mostrar credenciales de prueba
    with st.expander("💡 Credenciales de Prueba"):
        for proceso, creds in CREDENCIALES_ADMINISTRADORES.items():
            st.write(f"**{proceso}:** `{creds['usuario']}` / `{creds['password']}`")

def autenticar_administrador(proceso, usuario, password):
    """Autenticar credenciales"""
    if proceso in CREDENCIALES_ADMINISTRADORES:
        creds = CREDENCIALES_ADMINISTRADORES[proceso]
        return usuario == creds["usuario"] and password == creds["password"]
    return False

def obtener_solicitudes_del_proceso(gestor_datos, proceso_admin):
    """Obtener solicitudes del proceso específico"""
    df_todas = gestor_datos.obtener_todas_solicitudes()
    
    if df_todas.empty:
        return df_todas
    
    # Filtrar por proceso
    if 'proceso' in df_todas.columns:
        return df_todas[df_todas['proceso'] == proceso_admin]
    
    # Fallback para datos antiguos
    if 'area' in df_todas.columns:
        return df_todas[df_todas['area'] == proceso_admin]
    
    return pd.DataFrame()

def normalizar_datetime(dt):
    """Normalizar datetime a timezone-naive para comparaciones consistentes"""
    if dt is None:
        return None
    
    # Usar utilidad de zona horaria para consistencia
    return convertir_a_colombia(dt)

def mostrar_mini_dashboard(df, proceso):
    """Mini dashboard del proceso"""
    
    from timezone_utils_admin import obtener_fecha_actual_colombia
    st.subheader(f"📊 Dashboard - {proceso}")
    
    # Métricas principales
    col1, col2, col3, col4, col5 = st.columns(5)
    
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
        incompletas = len(df[df['estado'] == 'Incompleta'])
        st.metric("🟠 Incompletas", incompletas)
    
    with col5:
        completadas = len(df[df['estado'] == 'Completada'])
        st.metric("✅ Completadas", completadas)
    
    # Alertas
    if asignadas > 0:
        fecha_limite = obtener_fecha_actual_colombia() - timedelta(days=7)
        
        # Normalizar columnas datetime para comparación
        df_normalizado = df.copy()
        if 'fecha_solicitud' in df_normalizado.columns:
            df_normalizado['fecha_solicitud'] = df_normalizado['fecha_solicitud'].apply(normalizar_datetime)
            
            # Filtrar solicitudes pendientes antiguas
            antiguas = df_normalizado[
                (df_normalizado['estado'] == 'Asignada') & 
                (df_normalizado['fecha_solicitud'] < fecha_limite)
            ]
            
            if not antiguas.empty:
                st.warning(f"⚠️ {len(antiguas)} solicitudes Asignadas por más de 7 días")

    if incompletas > 0:
        # Buscar incompletas por mucho tiempo
        df_incompletas = df[df['estado'] == 'Incompleta']
        if not df_incompletas.empty and 'fecha_pausa' in df_incompletas.columns:
            from timezone_utils_admin import convertir_a_colombia, obtener_fecha_actual_colombia
            fecha_actual = obtener_fecha_actual_colombia()
            
            # Contar incompletas por más de 7 días
            incompletas_antiguas = 0
            for _, row in df_incompletas.iterrows():
                fecha_pausa = row.get('fecha_pausa')
                if fecha_pausa and pd.notna(fecha_pausa):
                    fecha_pausa_colombia = convertir_a_colombia(fecha_pausa)
                    if fecha_pausa_colombia:
                        dias_pausada = (fecha_actual - fecha_pausa_colombia).days
                        if dias_pausada > 7:
                            incompletas_antiguas += 1
            
            if incompletas_antiguas > 0:
                st.warning(f"⏸️ {incompletas_antiguas} solicitudes incompletas por más de 7 días")
    
    # Gráfico de estados
    if total > 0:
        datos_estados = df['estado'].value_counts()
        
        fig = go.Figure(data=[
            go.Pie(
                labels=datos_estados.index,
                values=datos_estados.values,
                hole=0.4,
                marker=dict(colors=['#FAD358', '#42A5F5', '#FD894A', '#66BB6A', '#EF5350'])
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

def mostrar_lista_solicitudes_administrador_mejorada(gestor_datos, df, proceso):
    """Lista mejorada con mejor gestión de estado"""
    
    df_filtrado = st.session_state.get('df_filtrado', df)
    
    if df_filtrado.empty:
        st.info("🔍 No se encontraron solicitudes con los filtros aplicados")
        return
    
    st.subheader("📋 Gestionar Solicitudes")
    
    # Ordenar por prioridad y fecha
    if 'prioridad' in df_filtrado.columns:
        orden_prioridad = {'Alta': 0, 'Media': 1, 'Baja': 2, 'Sin asignar': 3}
        df_filtrado = df_filtrado.copy()
        df_filtrado['orden_prioridad'] = df_filtrado['prioridad'].map(orden_prioridad).fillna(3)
        
        if 'fecha_solicitud' in df_filtrado.columns:
            df_filtrado['fecha_solicitud_normalizada'] = df_filtrado['fecha_solicitud'].apply(normalizar_datetime)
            df_filtrado = df_filtrado.sort_values(['orden_prioridad', 'fecha_solicitud_normalizada'])
        else:
            df_filtrado = df_filtrado.sort_values(['orden_prioridad'])
    
    # Mostrar cada solicitud con función mejorada
    for idx, solicitud in df_filtrado.iterrows():
        mostrar_solicitud_administrador_mejorada(gestor_datos, solicitud, proceso)
        
def mostrar_solicitud_administrador_mejorada(gestor_datos, solicitud, proceso):
    """Versión simplificada con UI más limpia"""
    from timezone_utils_admin import convertir_a_colombia, obtener_fecha_actual_colombia
    # Determinar color y emoji
    prioridad = solicitud.get('prioridad', 'Media')
    estado = solicitud['estado']
    
    if estado == 'Asignada':
        emoji = "🟡"
    elif estado == 'Completada':
        emoji = "✅"
    elif estado == 'En Proceso':
        emoji = "🔵"
    elif estado == 'Incompleta':
        emoji = "🟠"
    else:
        emoji = "📄"
    
    # Verificar actualizaciones recientes
    clave_actualizado_recientemente = f'actualizado_recientemente_{solicitud["id_solicitud"]}'
    actualizado_recientemente = st.session_state.get(clave_actualizado_recientemente, None)
    
    expandido = False
    mostrar_exito = False
    
    if actualizado_recientemente:
        diferencia_tiempo = obtener_fecha_actual_colombia() - actualizado_recientemente['timestamp']
        if diferencia_tiempo.total_seconds() < 30:
            expandido = True
            mostrar_exito = True
        else:
            del st.session_state[clave_actualizado_recientemente]
    
    # Título del expander
    titulo = f"{emoji} {solicitud['id_solicitud']} - {solicitud['nombre_solicitante']} ({estado})"
    if prioridad != 'Media':
        titulo += f" - {prioridad}"
    
    with st.expander(titulo, expanded=expandido):
        
        # Mostrar mensaje de éxito de actualización brevemente
        if actualizado_recientemente and mostrar_exito:
            st.success(f"✅ Solicitud Actualizada")

        # Alerta para solicitudes incompletas:
        if solicitud['estado'] == 'Incompleta':
            fecha_pausa = solicitud.get('fecha_pausa')
            if fecha_pausa and pd.notna(fecha_pausa):
                fecha_pausa_colombia = convertir_a_colombia(fecha_pausa)
                if fecha_pausa_colombia:
                    dias_pausada = (obtener_fecha_actual_colombia() - fecha_pausa_colombia).days
                    st.warning(f"⏸️ Solicitud PAUSADA desde hace {dias_pausada} días")
        
        # Información básica
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
                fecha_str = formatear_fecha_colombia(solicitud['fecha_solicitud'])
                st.write(f"**Fecha:** {fecha_str}")
        
        with col2:
            st.write("**📝 Descripción**")
            descripcion_limpia = limpiar_contenido_html(solicitud.get('descripcion', ''))
            st.text_area(
                "Descripción:",
                value=descripcion_limpia,
                height=100,
                disabled=True,
                key=f"desc_{solicitud['id_solicitud']}"
            )
        
        # Historial de comentarios administrativos
        st.markdown("---")
        comentarios_actuales = solicitud.get('comentarios_admin', '')

        if comentarios_actuales and comentarios_actuales.strip():
            st.markdown("**💬 Historial de Comentarios Administrativos**")
            comentario_limpio = limpiar_contenido_html(comentarios_actuales)
            st.info(f"**Comentario administrativo previo:** {comentario_limpio}")
        else:
            st.markdown("**💬 Sin comentarios administrativos previos**")

        # Comentarios adicionales del usuario
        comentarios_usuario = solicitud.get('comentarios_usuario', '')

        if comentarios_usuario and comentarios_usuario.strip():
            st.markdown("**👤 Comentarios Adicionales del Usuario**")
            comentario_limpio = limpiar_contenido_html(comentarios_usuario)
            st.success(f"**Comentarios adicionales del usuario:** {comentario_limpio}")
        else:
            st.markdown("**👤 Sin comentarios adicionales del usuario**")

        # Historial de pausas
        historial_pausas = solicitud.get('historial_pausas', '')
        if historial_pausas and historial_pausas.strip():
            st.markdown("---")
            st.markdown("**⏸️ Historial de Pausas**")
            with st.expander("Ver historial de pausas", expanded=False):
                st.text_area(
                    "Pausas:",
                    value=historial_pausas,
                    height=100,
                    disabled=True,
                    key=f"pausas_{solicitud['id_solicitud']}"
                )
        
        # Sección de archivos en expander
        st.markdown("---")
        with st.expander("📎 Archivos Adjuntos", expanded=False):
            mostrar_archivos_adjuntos_administrador(gestor_datos, solicitud['id_solicitud'])
        
        st.markdown("---")
        
        # Formulario de gestión simplificado
        with st.form(f"gestionar_{solicitud['id_solicitud']}"):
        
            col1, col2 = st.columns(2)
            
            with col1:
                nuevo_estado = st.selectbox(
                    "Estado:",
                    options=["Asignada", "En Proceso", "Incompleta", "Completada", "Cancelada"],
                    index=["Asignada", "En Proceso", "Incompleta", "Completada", "Cancelada"].index(solicitud['estado']),
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
                clave_contador = f'contador_comentario_{solicitud["id_solicitud"]}'
                contador_comentario = st.session_state.get(clave_contador, 0)

                nuevo_comentario = st.text_area(
                    "Nuevo comentario:",
                    placeholder="Escriba aquí el nuevo comentario...",
                    height=100,
                    key=f"comentarios_{solicitud['id_solicitud']}_{contador_comentario}"
                )
                
                email_responsable = st.text_input(
                    "Email responsable:",
                    placeholder="responsable@igac.gov.co",
                    key=f"email_resp_{solicitud['id_solicitud']}"
                )
            
            # Subida de archivos
            archivos_nuevos = st.file_uploader(
                "Subir archivos:",
                accept_multiple_files=True,
                type=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'jpg', 'jpeg', 'png', 'zip'],
                key=f"archivos_admin_{solicitud['id_solicitud']}"
            )
            
            # Opciones de notificación
            col1, col2 = st.columns(2)
            with col1:
                notificar_solicitante = st.checkbox(
                    "📧 Notificar al solicitante",
                    value=True,
                    key=f"notificar_usuario_{solicitud['id_solicitud']}"
                )
            
            with col2:
                notificar_responsable = st.checkbox(
                    "📧 Notificar al responsable",
                    value=False if not email_responsable else True,
                    key=f"notificar_resp_{solicitud['id_solicitud']}"
                )
            
            # Botón actualizar
            actualizar = st.form_submit_button(
                "💾 Actualizar",
                type="primary",
                use_container_width=True
            )
            
            # Procesar actualización
            if actualizar:
                procesar_actualizacion_sharepoint_simplificada(
                    gestor_datos, solicitud, nuevo_estado, nueva_prioridad, 
                    responsable, email_responsable, nuevo_comentario,
                    notificar_solicitante, notificar_responsable, archivos_nuevos
                )

def mostrar_archivos_adjuntos_administrador(gestor_datos, id_solicitud):
    """Mostrar archivos adjuntos con layout mejorado desde seguimiento"""
    
    try:
        # Obtener archivos adjuntos para esta solicitud
        archivos_adjuntos = gestor_datos.obtener_archivos_adjuntos_solicitud(id_solicitud)
        
        if archivos_adjuntos:
            st.success(f"📁 Se encontraron {len(archivos_adjuntos)} archivo(s) adjunto(s)")
            
            # Mostrar cada archivo adjunto
            for i, archivo in enumerate(archivos_adjuntos):
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    tamaño_archivo_mb = archivo['size'] / (1024 * 1024)
                    st.write(f"📄 **{archivo['name']}** ({tamaño_archivo_mb:.2f} MB)")
                    
                    # Mostrar fecha de creación del archivo si está disponible
                    if archivo.get('created'):
                        try:
                            fecha_creacion = datetime.fromisoformat(archivo['created'].replace('Z', '+00:00'))
                            fecha_str = formatear_fecha_colombia(fecha_creacion)
                            st.caption(f"📅 Subido: {fecha_str}")
                        except:
                            st.caption("📅 Fecha no disponible")
                    else:
                        st.caption("📅 Fecha no disponible")
                
                with col2:
                    # Botón descargar
                    if archivo.get('download_url'):
                        st.markdown(f"[⬇️ Descargar]({archivo['download_url']})")
                    else:
                        st.info("🔗 Link no disponible")
                
                with col3:
                    # Botón ver en navegador para tipos de archivo soportados
                    if archivo.get('web_url'):
                        extension_archivo = archivo['name'].lower().split('.')[-1] if '.' in archivo['name'] else ''
                        if extension_archivo in ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'doc', 'docx', 'xls', 'xlsx']:
                            st.markdown(f"[👁️ Ver]({archivo['web_url']})")
                        else:
                            st.info("👁️ No disponible")
                    else:
                        st.info("👁️ No disponible")
                
                # Agregar línea separadora entre archivos
                if i < len(archivos_adjuntos) - 1:
                    st.markdown("---")
        else:
            st.info("📭 No hay archivos adjuntos para esta solicitud")
    
    except Exception as e:
        st.warning("⚠️ Error al cargar archivos adjuntos")
        print(f"Error cargando archivos adjuntos para admin: {e}")

def procesar_actualizacion_sharepoint_simplificada(gestor_datos, solicitud, nuevo_estado, nueva_prioridad, 
                                                  responsable, email_responsable, nuevo_comentario,
                                                  notificar_solicitante, notificar_responsable, archivos_nuevos=None):
    """Proceso de actualización simplificado y confiable"""
    
    try:

        # Validación de transiciones de estado:
        estado_actual = solicitud['estado']
        
        # Validar transición a Completada desde Incompleta
        if estado_actual == 'Incompleta' and nuevo_estado == 'Completada':
            st.error("❌ No se puede completar una solicitud incompleta. Primero reanúdela cambiando a 'En Proceso'.")
            return False


        # Rastrear qué cambió realmente
        cambios = {}
        
        # Paso 1: Verificar qué cambió
        if nuevo_estado != solicitud['estado']:
            cambios['estado'] = {'old': solicitud['estado'], 'new': nuevo_estado}
        
        if nueva_prioridad != solicitud.get('prioridad', 'Media'):
            cambios['prioridad'] = {'old': solicitud.get('prioridad', 'Media'), 'new': nueva_prioridad}
        
        if responsable and responsable != solicitud.get('responsable_asignado', ''):
            cambios['responsable'] = {'old': solicitud.get('responsable_asignado', ''), 'new': responsable}
        
        if nuevo_comentario and nuevo_comentario.strip():
            cambios['comentario'] = {'new': nuevo_comentario.strip()}
        
        # Paso 2: Preparar comentarios con cambio automático de estado si es necesario
        comentarios_actuales = solicitud.get('comentarios_admin', '')
        
        if nuevo_comentario and nuevo_comentario.strip():
            autor = responsable or st.session_state.get('usuario_admin', 'Admin')
            comentarios_finales = agregar_comentario_administrador(
                comentarios_actuales, 
                nuevo_comentario.strip(), 
                autor
            )
        else:
            comentarios_finales = comentarios_actuales
            # Comentarios automáticos para incluir pausas:
            if 'estado' in cambios:
                autor = st.session_state.get('usuario_admin', 'Admin')
                if nuevo_estado == 'Incompleta':
                    comentario_automatico = f"Solicitud PAUSADA - Estado cambiado a 'Incompleta'"
                elif estado_actual == 'Incompleta':
                    comentario_automatico = f"Solicitud REANUDADA - Estado cambiado de 'Incompleta' a '{nuevo_estado}'"
                else:
                    comentario_automatico = f"Estado cambiado de '{cambios['estado']['old']}' a '{cambios['estado']['new']}'"
                
                comentarios_finales = agregar_comentario_administrador(
                    comentarios_actuales, 
                    comentario_automatico, 
                    f"{autor} (Sistema)"
                )
        
        # Paso 3: Actualizar en SharePoint (transacción única)
        with st.spinner("🔄 Actualizando solicitud..."):
            
            # Actualizar prioridad si cambió
            if 'prioridad' in cambios:
                exito_prioridad = gestor_datos.actualizar_prioridad_solicitud(solicitud['id_solicitud'], nueva_prioridad)
                if not exito_prioridad:
                    st.error("❌ Error al actualizar prioridad")
                    return False
            
            # Actualizar estado y comentarios
            exito_estado = gestor_datos.actualizar_estado_solicitud(
                solicitud['id_solicitud'],
                nuevo_estado,
                responsable,
                comentarios_finales
            )
            
            if not exito_estado:
                st.error("❌ Error al actualizar la solicitud")
                return False
            
            # Manejar subida de archivos
            archivos_subidos = []
            if archivos_nuevos:
                for archivo_subido in archivos_nuevos:
                    if archivo_subido.size <= 10 * 1024 * 1024:  # Límite 10MB
                        try:
                            datos_archivo = archivo_subido.read()
                            exito = gestor_datos.subir_archivo_adjunto_a_item(
                                solicitud['id_solicitud'], datos_archivo, archivo_subido.name
                            )
                            if exito:
                                archivos_subidos.append(archivo_subido.name)
                        except Exception:
                            continue  # Saltar subidas fallidas
            
            if archivos_subidos:
                cambios['archivos'] = {'new': archivos_subidos}
        
        # Paso 4: Enviar notificaciones al solicitante solo si se solicita y ocurrieron cambios
        email_enviado = False
        if notificar_solicitante and cambios:
            try:
                gestor_email = GestorNotificacionesEmail()
                
                datos_solicitud = {
                    'id_solicitud': solicitud['id_solicitud'],
                    'tipo_solicitud': solicitud['tipo_solicitud'],
                    'email_solicitante': solicitud['email_solicitante'],
                    'fecha_solicitud': solicitud.get('fecha_solicitud'),
                    'area': solicitud.get('area', 'N/A'),
                    'proceso': solicitud.get('proceso', 'N/A')
                }
                
                # Enviar notificación sin adjuntos
                email_enviado = gestor_email.enviar_notificacion_actualizacion_solo_cambios(
                    datos_solicitud, cambios, responsable, email_responsable
                )
                        
            except Exception as e:
                print(f"Error en notificación por email: {e}")
                
        # Paso 4b: Notificación opcional al responsable
        email_responsable_enviado = False
        if notificar_responsable and email_responsable and email_responsable.strip() and cambios:
            try:
                datos_responsable = {
                    'id_solicitud': solicitud['id_solicitud'],
                    'tipo_solicitud': solicitud['tipo_solicitud'],
                    'email_solicitante': solicitud['email_solicitante'],
                    'nombre_solicitante': solicitud['nombre_solicitante'],
                    'fecha_solicitud': solicitud.get('fecha_solicitud'),
                    'area': solicitud.get('area', 'N/A'),
                    'proceso': solicitud.get('proceso', 'N/A')
                }
                
                email_responsable_enviado = gestor_email.enviar_notificacion_responsable(
                    datos_responsable, cambios, responsable, email_responsable
                )
                
            except Exception as e:
                print(f"Error en notificación de responsable: {e}")

        # Paso 5: Recargar datos y mostrar éxito
        gestor_datos.cargar_datos(forzar_recarga=True)


        # Borrar cache y forzar actualización
        invalidar_y_actualizar_cache()
       
        # Mostrar mensaje de éxito limpio
        st.success(f"✅ Solicitud {solicitud['id_solicitud']} actualizada correctamente")
        
        if cambios:
            textos_cambios = []
            if 'estado' in cambios:
                textos_cambios.append(f"Estado: {cambios['estado']['new']}")
            if 'prioridad' in cambios:
                textos_cambios.append(f"Prioridad: {cambios['prioridad']['new']}")
            if 'responsable' in cambios:
                textos_cambios.append(f"Responsable: {cambios['responsable']['new']}")
            if 'comentario' in cambios:
                textos_cambios.append("Nuevo comentario agregado")
            if 'archivos' in cambios:
                textos_cambios.append(f"{len(cambios['archivos']['new'])} archivo(s) subido(s)")
            
            if email_enviado:
                textos_cambios.append("Notificación enviada al solicitante")

            if email_responsable_enviado:
                textos_cambios.append(f"Notificación enviada a {email_responsable}")
            
            st.info("🔄 Cambios: " + " | ".join(textos_cambios))
        
        # Marcar para retroalimentación de UI
        st.session_state[f'actualizado_recientemente_{solicitud["id_solicitud"]}'] = {
            'timestamp': obtener_fecha_actual_colombia(),
            'nuevo_estado': nuevo_estado
        }
        
        # Incrementar contador de comentarios para forzar nuevo widget
        if nuevo_comentario and nuevo_comentario.strip():
            clave_contador = f'contador_comentario_{solicitud["id_solicitud"]}'
            contador_actual = st.session_state.get(clave_contador, 0)
            st.session_state[clave_contador] = contador_actual + 1
            st.rerun()
        
        return True
            
    except Exception as e:
        st.error(f"❌ Error al procesar actualización: {str(e)}")
        return False