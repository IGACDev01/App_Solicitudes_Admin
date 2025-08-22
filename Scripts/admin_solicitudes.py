import streamlit as st
import pandas as pd
from email_manager import GestorNotificacionesEmail
import plotly.graph_objects as go
from timezone_utils_admin import obtener_fecha_actual_colombia, convertir_a_colombia, formatear_fecha_colombia
from utils import invalidar_y_actualizar_cache
import time
from datetime import datetime, timedelta

# Credenciales por proceso
CREDENCIALES_ADMINISTRADORES = {
    "Almacén": {"usuario": "admin_almacen", "password": "Almacen3455*"},
    "Archivo": {"usuario": "admin_archivo", "password": "Archivo4790*"},
    "Contabilidad": {"usuario": "admin_contabilidad", "password": "Contable9865#"},
    "Contractual": {"usuario": "admin_contractual", "password": "Contractual6518!"},
    "Correspondencia": {"usuario": "admin_correspondencia", "password": "Correo3981$"},
    "Infraestructura": {"usuario": "admin_infraestructura", "password": "Infraestructura2387!"},
    "Operación Logística SAF": {"usuario": "admin_operacion", "password": "Logistica0978#"},
    "Presupuesto": {"usuario": "admin_presupuesto", "password": "Presupuesto3425$"},
    "Tesorería": {"usuario": "admin_tesoreria", "password": "Tesoreria9248!"},
    "Tiquetes": {"usuario": "admin_tiquetes", "password": "Tiquetes9845$"},
    "Transporte": {"usuario": "admin_transporte", "password": "Transporte5926*"}
}

# Configuración de persistencia
TIEMPO_PERSISTENCIA_EXPANDER = 300  # 5 minutos en segundos
TIEMPO_PERSISTENCIA_ARCHIVOS = 600  # 10 minutos en segundos

import time
from datetime import datetime, timedelta

# Configuración de persistencia
TIEMPO_PERSISTENCIA_EXPANDER = 300  # 5 minutos en segundos
TIEMPO_PERSISTENCIA_ARCHIVOS = 600  # 10 minutos en segundos


def inicializar_estados_persistentes():
    """Inicializar estados persistentes al cargar la aplicación"""
    if 'estados_persistentes_inicializados' not in st.session_state:
        st.session_state.estados_persistentes_inicializados = True
        st.session_state.expanders_persistentes = {}
        st.session_state.archivos_cache_persistente = {}
        st.session_state.timestamp_inicializacion = time.time()

def mantener_estado_expander_persistente(id_solicitud, forzar_abierto=False, accion=None):
    """Mantener estado del expander de forma persistente"""
    inicializar_estados_persistentes()

    key = f"expander_{id_solicitud}"
    timestamp_actual = time.time()

    # Si se fuerza abrir o hay una acción específica
    if forzar_abierto or accion:
        st.session_state.expanders_persistentes[key] = {
            'expandido': True,
            'timestamp': timestamp_actual,
            'accion': accion or 'manual',
            'persistente': True
        }
        return True

    # Verificar estado existente
    estado = st.session_state.expanders_persistentes.get(key)
    if estado and estado.get('persistente'):
        # Verificar si no ha expirado
        tiempo_transcurrido = timestamp_actual - estado['timestamp']
        if tiempo_transcurrido < TIEMPO_PERSISTENCIA_EXPANDER:
            return estado['expandido']
        else:
            # Limpiar estado expirado
            if key in st.session_state.expanders_persistentes:
                del st.session_state.expanders_persistentes[key]

    return False

def cache_archivos_persistente(id_solicitud, archivos=None):
    """Cache persistente para archivos adjuntos"""
    inicializar_estados_persistentes()

    key = f"archivos_{id_solicitud}"
    timestamp_actual = time.time()

    # Guardar archivos en cache
    if archivos is not None:
        st.session_state.archivos_cache_persistente[key] = {
            'archivos': archivos,
            'timestamp': timestamp_actual,
            'cargado': True
        }
        return archivos

    # Recuperar del cache
    cache = st.session_state.archivos_cache_persistente.get(key)
    if cache:
        tiempo_transcurrido = timestamp_actual - cache['timestamp']
        if tiempo_transcurrido < TIEMPO_PERSISTENCIA_ARCHIVOS:
            return cache['archivos']
        else:
            # Limpiar cache expirado
            if key in st.session_state.archivos_cache_persistente:
                del st.session_state.archivos_cache_persistente[key]

    return None

def limpiar_estados_expirados():
    """Limpiar estados expirados periódicamente"""
    if not hasattr(st.session_state, 'expanders_persistentes'):
        return

    timestamp_actual = time.time()

    # Limpiar expanders expirados
    keys_expirados = []
    for key, estado in st.session_state.expanders_persistentes.items():
        if timestamp_actual - estado['timestamp'] > TIEMPO_PERSISTENCIA_EXPANDER:
            keys_expirados.append(key)

    for key in keys_expirados:
        del st.session_state.expanders_persistentes[key]

    # Limpiar cache de archivos expirado
    keys_cache_expirados = []
    for key, cache in st.session_state.archivos_cache_persistente.items():
        if timestamp_actual - cache['timestamp'] > TIEMPO_PERSISTENCIA_ARCHIVOS:
            keys_cache_expirados.append(key)

    for key in keys_cache_expirados:
        del st.session_state.archivos_cache_persistente[key]

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

    # Inicializar estados persistentes
    inicializar_estados_persistentes()

    # Limpiar estados expirados cada vez
    limpiar_estados_expirados()

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
    """Filtros y búsqueda simplificados con paginación limpia"""
    st.subheader("🔍 Filtros y Búsqueda")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Filtro múltiple de estados con solicitudes activas por defecto
        estados_disponibles = list(df['estado'].unique())
        estados_activos = [estado for estado in estados_disponibles if estado not in ['Completada', 'Cancelada']]

        filtros_estado = st.multiselect(
            "Estados:",
            options=estados_disponibles,
            default=estados_activos,
            key="filtros_estado_multi"
        )

    with col2:
        # Filtro múltiple de prioridades
        if 'prioridad' in df.columns:
            prioridades_disponibles = list(df['prioridad'].unique())
            filtros_prioridad = st.multiselect(
                "Prioridades:",
                options=prioridades_disponibles,
                default=[],
                key="filtros_prioridad_multi"
            )
        else:
            filtros_prioridad = []

    with col3:
        busqueda = st.text_input(
            "Buscar por ID o nombre:",
            placeholder="ID123 o Juan Pérez",
            key="busqueda_admin"
        )

    # Aplicar filtros
    df_filtrado = df

    # Filtro de estados (múltiple)
    if filtros_estado:
        df_filtrado = df_filtrado[df_filtrado['estado'].isin(filtros_estado)]

    # Filtro de prioridades (múltiple)
    if filtros_prioridad and 'prioridad' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['prioridad'].isin(filtros_prioridad)]

    # Búsqueda de texto
    if busqueda:
        mask = (
                df_filtrado['id_solicitud'].str.contains(busqueda, case=False, na=False) |
                df_filtrado['nombre_solicitante'].str.contains(busqueda, case=False, na=False)
        )
        df_filtrado = df_filtrado[mask]

    # === NUEVO: Ordenar TODAS las solicitudes filtradas por fecha (más reciente primero) ===
    if 'fecha_solicitud' in df_filtrado.columns and not df_filtrado.empty:
        df_filtrado = df_filtrado.assign(
            fecha_solicitud_normalizada=df_filtrado['fecha_solicitud'].apply(normalizar_datetime)
        ).sort_values('fecha_solicitud_normalizada', ascending=False)

        # Remover la columna auxiliar
        df_filtrado = df_filtrado.drop('fecha_solicitud_normalizada', axis=1)

    # Paginación simple (10 elementos fijos)
    solicitudes_por_pagina = 5
    total_solicitudes = len(df_filtrado)
    total_paginas = max(1, (total_solicitudes - 1) // solicitudes_por_pagina + 1)

    # Inicializar página actual si no existe
    if 'pagina_actual' not in st.session_state:
        st.session_state.pagina_actual = 1

    # Validar que la página actual no exceda el total
    if st.session_state.pagina_actual > total_paginas:
        st.session_state.pagina_actual = 1

    pagina_actual = st.session_state.pagina_actual

    # Aplicar paginación
    inicio = (pagina_actual - 1) * solicitudes_por_pagina
    fin = inicio + solicitudes_por_pagina
    df_paginado = df_filtrado.iloc[inicio:fin]

    # Guardar DataFrames en session state
    st.session_state.df_filtrado = df_filtrado
    st.session_state.df_paginado = df_paginado
    st.session_state.total_paginas = total_paginas

    # Mostrar información de resultados
    if total_solicitudes > 0:
        st.write(f"📋 Mostrando {len(df_paginado)} de {total_solicitudes} solicitudes")
    else:
        st.write("📋 No se encontraron solicitudes")

def mostrar_paginacion():
    """Mostrar controles de paginación estilo limpio"""
    pagina_actual = st.session_state.get('pagina_actual', 1)
    total_paginas = st.session_state.get('total_paginas', 1)

    if total_paginas <= 1:
        return

    st.markdown("---")

    # Crear columnas para centrar la paginación
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # Crear botones de paginación
        cols = st.columns([1, 1, 3, 1, 1])

        # Botón anterior
        with cols[0]:
            if st.button("◀", disabled=(pagina_actual <= 1), key="prev_page"):
                st.session_state.pagina_actual = max(1, pagina_actual - 1)
                st.rerun()

        # Números de página como botones
        with cols[2]:
            # Mostrar páginas como botones (máximo 5 páginas visibles)
            paginas_a_mostrar = []

            if total_paginas <= 5:
                paginas_a_mostrar = list(range(1, total_paginas + 1))
            else:
                if pagina_actual <= 3:
                    paginas_a_mostrar = [1, 2, 3, 4, 5]
                elif pagina_actual >= total_paginas - 2:
                    paginas_a_mostrar = list(range(total_paginas - 4, total_paginas + 1))
                else:
                    paginas_a_mostrar = list(range(pagina_actual - 2, pagina_actual + 3))

            # Crear mini-columnas para cada número de página
            mini_cols = st.columns(len(paginas_a_mostrar))

            for i, pagina in enumerate(paginas_a_mostrar):
                with mini_cols[i]:
                    if pagina == pagina_actual:
                        st.markdown(
                            f"<div style='background: #007bff; color: white; text-align: center; padding: 4px; border-radius: 4px; margin: 2px;'>{pagina}</div>",
                            unsafe_allow_html=True)
                    else:
                        if st.button(str(pagina), key=f"page_{pagina}"):
                            st.session_state.pagina_actual = pagina
                            st.rerun()

        # Botón siguiente
        with cols[4]:
            if st.button("▶", disabled=(pagina_actual >= total_paginas), key="next_page"):
                st.session_state.pagina_actual = min(total_paginas, pagina_actual + 1)
                st.rerun()

def mostrar_lista_solicitudes_administrador_mejorada(gestor_datos, df, proceso):
    """Lista mejorada con mejor gestión de estado y paginación"""

    df_paginado = st.session_state.get('df_paginado', df.head(10))

    if df_paginado.empty:
        st.info("🔍 No se encontraron solicitudes con los filtros aplicados")
        return

    st.subheader("📋 Gestionar Solicitudes")

    # Las solicitudes ya vienen ordenadas por fecha desde mostrar_filtros_busqueda
    # No necesitamos ordenar aquí

    # Mostrar cada solicitud de manera optimizada
    for idx, solicitud in df_paginado.iterrows():
        mostrar_solicitud_administrador_mejorada(gestor_datos, solicitud, proceso)

    # Paginación al final
    mostrar_paginacion()

def mostrar_solicitud_administrador_mejorada(gestor_datos, solicitud, proceso):
    """Versión con super lazy loading - archivos solo se cargan al hacer clic"""
    from timezone_utils_admin import obtener_fecha_actual_colombia

    # === DATOS LIGEROS (siempre se cargan) ===
    estado = solicitud['estado']
    prioridad = solicitud.get('prioridad', 'Media')

    # Emojis y título (operaciones ligeras)
    emoji_map = {
        'Asignada': "🟡", 'Completada': "✅", 'En Proceso': "🔵",
        'Incompleta': "🟠", 'Cancelada': "❌"
    }
    emoji = emoji_map.get(estado, "📄")

    # Título del expander (solo datos básicos)
    titulo = f"{emoji} {solicitud['id_solicitud']} - {solicitud['nombre_solicitante']} ({estado})"
    if prioridad not in ['Media', 'Por definir']:
        titulo += f" - {prioridad}"

    # Verificar si fue actualizado recientemente
    actualizado_recientemente = st.session_state.get(f'actualizado_recientemente_{solicitud["id_solicitud"]}', None)
    expandido_por_actualizacion = False
    if actualizado_recientemente:
        diferencia_tiempo = obtener_fecha_actual_colombia() - actualizado_recientemente['timestamp']
        expandido_por_actualizacion = diferencia_tiempo.total_seconds() < 30

    # === EXPANDER PERSISTENTE ===
    # Verificar estados de persistencia
    expandido_por_persistencia = mantener_estado_expander_persistente(solicitud['id_solicitud'])
    expandido_final = expandido_por_actualizacion or expandido_por_persistencia

    # Crear expander persistente
    with st.expander(titulo, expanded=expandido_final):
        # Marcar como abierto manualmente si se expande
        if expandido_final and not expandido_por_actualizacion:
            mantener_estado_expander_persistente(solicitud['id_solicitud'], forzar_abierto=True, accion='manual')

        # Mensaje de éxito si fue actualizado
        if actualizado_recientemente and expandido_por_actualizacion:
            st.success("✅ Solicitud Actualizada")

        # === DATOS PESADOS (solo si el expander está abierto) ===
        expander_data_key = f"expander_data_loaded_{solicitud['id_solicitud']}"

        # Cargar datos pesados solo una vez por sesión
        if expander_data_key not in st.session_state:
            st.session_state[expander_data_key] = {
                'descripcion_procesada': None,
                'comentarios_procesados': None,
                'historial_pausas': None
            }

        datos_cache = st.session_state[expander_data_key]

        # === INFORMACIÓN BÁSICA (ligera) ===
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

            # Procesar descripción solo si no está en cache
            if datos_cache['descripcion_procesada'] is None:
                descripcion_limpia = limpiar_contenido_html(solicitud.get('descripcion', ''))
                datos_cache['descripcion_procesada'] = descripcion_limpia

            st.text_area(
                "Descripción:",
                value=datos_cache['descripcion_procesada'],
                height=100,
                disabled=True,
                key=f"desc_{solicitud['id_solicitud']}"
            )

        # === COMENTARIOS ADMINISTRATIVOS (procesamiento pesado) ===
        st.markdown("---")

        if datos_cache['comentarios_procesados'] is None:
            comentarios_actuales = solicitud.get('comentarios_admin', '')
            if comentarios_actuales and comentarios_actuales.strip():
                datos_cache['comentarios_procesados'] = limpiar_contenido_html(comentarios_actuales)
            else:
                datos_cache['comentarios_procesados'] = ""

        if datos_cache['comentarios_procesados']:
            st.markdown("**💬 Historial de Comentarios Administrativos**")
            with st.expander("Ver comentarios completos", expanded=False):
                st.info(f"**Comentarios:** {datos_cache['comentarios_procesados']}")
        else:
            st.markdown("**💬 Sin comentarios administrativos previos**")

        # === COMENTARIOS DEL USUARIO ===
        comentarios_usuario = solicitud.get('comentarios_usuario', '')
        if comentarios_usuario and comentarios_usuario.strip():
            st.markdown("**👤 Comentarios Adicionales del Usuario**")
            comentario_usuario_limpio = limpiar_contenido_html(comentarios_usuario)
            st.success(f"**Comentarios del usuario:** {comentario_usuario_limpio}")

        # === HISTORIAL DE PAUSAS (pesado) ===
        if datos_cache['historial_pausas'] is None:
            historial_pausas = solicitud.get('historial_pausas', '')
            datos_cache['historial_pausas'] = historial_pausas

        if datos_cache['historial_pausas'] and datos_cache['historial_pausas'].strip():
            st.markdown("---")
            with st.expander("⏸️ Ver historial de pausas", expanded=False):
                st.text_area(
                    "Pausas:",
                    value=datos_cache['historial_pausas'],
                    height=100,
                    disabled=True,
                    key=f"pausas_{solicitud['id_solicitud']}"
                )

        # === ARCHIVOS ADJUNTOS PERSISTENTES ===
        st.markdown("---")
        st.markdown("**📎 Archivos Adjuntos**")

        id_solicitud = solicitud['id_solicitud']

        # Verificar cache persistente primero
        archivos_cached = cache_archivos_persistente(id_solicitud)

        if archivos_cached is not None:
            # Mostrar archivos desde cache persistente
            if archivos_cached:
                st.success(f"📁 {len(archivos_cached)} archivo(s) encontrado(s)")

                for archivo in archivos_cached:
                    col1, col2, col3 = st.columns([3, 1, 1])

                    with col1:
                        tamaño_mb = archivo['size'] / (1024 * 1024)
                        st.write(f"📄 **{archivo['name']}** ({tamaño_mb:.2f} MB)")

                        if archivo.get('created'):
                            try:
                                from datetime import datetime
                                fecha_creacion = datetime.fromisoformat(archivo['created'].replace('Z', '+00:00'))
                                fecha_str = formatear_fecha_colombia(fecha_creacion)
                                st.caption(f"📅 Subido: {fecha_str}")
                            except:
                                st.caption("📅 Fecha no disponible")

                    with col2:
                        if archivo.get('download_url'):
                            st.markdown(f"[⬇️ Descargar]({archivo['download_url']})")
                        else:
                            st.info("🔗 Link no disponible")

                    with col3:
                        if archivo.get('web_url'):
                            st.markdown(f"[👁️ Ver]({archivo['web_url']})")
                        else:
                            st.info("👁️ No disponible")

                    if archivo != archivos_cached[-1]:
                        st.markdown("---")

                # Botón para refrescar archivos
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    if st.button("🔄 Actualizar", key=f"refresh_files_{id_solicitud}"):
                        # Limpiar cache y mantener expander abierto
                        st.session_state.archivos_cache_persistente.pop(f"archivos_{id_solicitud}", None)
                        mantener_estado_expander_persistente(id_solicitud, forzar_abierto=True, accion='refresh_archivos')
                        st.rerun()
            else:
                st.info("🔭 No hay archivos adjuntos para esta solicitud")

                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    if st.button("🔄 Verificar de nuevo", key=f"recheck_files_{id_solicitud}"):
                        # Limpiar cache y mantener expander abierto
                        st.session_state.archivos_cache_persistente.pop(f"archivos_{id_solicitud}", None)
                        mantener_estado_expander_persistente(id_solicitud, forzar_abierto=True, accion='recheck_archivos')
                        st.rerun()

        else:
            # No hay cache, mostrar botón para cargar
            loading_key = f"loading_archivos_{id_solicitud}"

            if st.session_state.get(loading_key, False):
                st.info("🔄 Cargando archivos adjuntos...")

                # Cargar archivos y guardar en cache persistente
                try:
                    archivos_adjuntos = gestor_datos.obtener_archivos_adjuntos_solicitud(id_solicitud)
                    # Guardar en cache persistente
                    cache_archivos_persistente(id_solicitud, archivos_adjuntos)
                    # Mantener expander abierto
                    mantener_estado_expander_persistente(id_solicitud, forzar_abierto=True, accion='cargar_archivos')
                    st.session_state[loading_key] = False
                    st.rerun()
                except Exception as e:
                    cache_archivos_persistente(id_solicitud, [])
                    st.session_state[loading_key] = False
                    st.error(f"❌ Error al cargar archivos: {str(e)}")
            else:
                col1, col2 = st.columns([1, 2])

                with col1:
                    cargar_archivos = st.button(
                        "📁 Cargar archivos adjuntos",
                        key=f"load_files_{id_solicitud}",
                        help="Haz clic para cargar y ver archivos adjuntos"
                    )

                with col2:
                    st.caption("👆 Los archivos se cargan solo cuando los necesites")

                if cargar_archivos:
                    st.session_state[loading_key] = True
                    # Mantener expander abierto durante la carga
                    mantener_estado_expander_persistente(id_solicitud, forzar_abierto=True, accion='iniciar_carga')
                    st.rerun()

        st.markdown("---")

        # === FORMULARIO DE GESTIÓN (ligero) ===
        with st.form(f"gestionar_{solicitud['id_solicitud']}"):
            col1, col2 = st.columns(2)

            with col1:
                nuevo_estado = st.selectbox(
                    "Estado:",
                    options=["Asignada", "En Proceso", "Incompleta", "Completada", "Cancelada"],
                    index=["Asignada", "En Proceso", "Incompleta", "Completada", "Cancelada"].index(
                        solicitud['estado']),
                    key=f"estado_{solicitud['id_solicitud']}"
                )

                prioridad_actual = solicitud.get('prioridad', 'Media')
                nueva_prioridad = st.selectbox(
                    "Prioridad:",
                    options=["Por definir", "Alta", "Media", "Baja"],
                    index=["Por definir", "Alta", "Media", "Baja"].index(prioridad_actual) if prioridad_actual in [
                        "Por definir", "Alta", "Media", "Baja"] else 2,
                    key=f"prioridad_{solicitud['id_solicitud']}"
                )

                responsable = st.text_input(
                    "Responsable:",
                    value=solicitud.get('responsable_asignado', ''),
                    key=f"responsable_{solicitud['id_solicitud']}"
                )

            with col2:
                nuevo_comentario = st.text_area(
                    "Nuevo comentario:",
                    placeholder="Escriba aquí el nuevo comentario...",
                    height=100,
                    key=f"comentarios_{solicitud['id_solicitud']}"
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
            actualizar = st.form_submit_button("💾 Actualizar", type="primary", use_container_width=True)

            # Procesar actualización
            if actualizar:
                # Limpiar cache de datos pesados para forzar recarga después de actualización
                if expander_data_key in st.session_state:
                    del st.session_state[expander_data_key]

                # Limpiar cache de archivos para que se recarguen con archivos nuevos
                archivos_cache_key = f"archivos_{id_solicitud}"
                if archivos_cache_key in st.session_state.get('archivos_cache_persistente', {}):
                    del st.session_state.archivos_cache_persistente[archivos_cache_key]

                procesar_actualizacion_sharepoint_simplificada(
                    gestor_datos, solicitud, nuevo_estado, nueva_prioridad,
                    responsable, email_responsable, nuevo_comentario,
                    notificar_solicitante, notificar_responsable, archivos_nuevos
                )

def preservar_estado_expander(id_solicitud, accion_realizada=None):
    """Preservar el estado del expander después de acciones"""
    estado_key = f"expander_preservado_{id_solicitud}"

    if accion_realizada:
        # Marcar que se realizó una acción para mantener abierto
        st.session_state[estado_key] = {
            'expandido': True,
            'timestamp': obtener_fecha_actual_colombia(),
            'accion': accion_realizada
        }

    # Verificar si debe mantenerse expandido
    estado = st.session_state.get(estado_key)
    if estado and estado.get('expandido'):
        # Mantener expandido por 10 segundos después de la acción
        tiempo_transcurrido = (obtener_fecha_actual_colombia() - estado['timestamp']).total_seconds()
        return tiempo_transcurrido < 10

    return False

def mostrar_archivos_adjuntos_administrador_inline(gestor_datos, id_solicitud):
    """Versión inline optimizada para cargar archivos"""
    try:
        archivos_adjuntos = gestor_datos.obtener_archivos_adjuntos_solicitud(id_solicitud)
        mostrar_lista_archivos_simple(archivos_adjuntos)
        return archivos_adjuntos
    except Exception as e:
        st.warning("⚠️ Error al cargar archivos adjuntos")
        return []

def mostrar_lista_archivos_simple(archivos_adjuntos):
    """Mostrar lista simple de archivos"""
    if archivos_adjuntos:
        st.success(f"📁 Se encontraron {len(archivos_adjuntos)} archivo(s)")

        for archivo in archivos_adjuntos:
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                tamaño_mb = archivo['size'] / (1024 * 1024)
                st.write(f"📄 **{archivo['name']}** ({tamaño_mb:.2f} MB)")

            with col2:
                if archivo.get('download_url'):
                    st.markdown(f"[⬇️ Descargar]({archivo['download_url']})")

            with col3:
                if archivo.get('web_url'):
                    st.markdown(f"[👁️ Ver]({archivo['web_url']})")
    else:
        st.info("📭 No hay archivos adjuntos")

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
                exito_prioridad = gestor_datos.actualizar_prioridad_solicitud(solicitud['id_solicitud'],
                                                                              nueva_prioridad)
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

        # Mantener expander abierto después de actualización
        mantener_estado_expander_persistente(solicitud['id_solicitud'], forzar_abierto=True, accion='actualizacion')

        # Invalidar cache de archivos si se subieron nuevos
        if 'archivos' in cambios:
            archivos_cache_key = f"archivos_{solicitud['id_solicitud']}"
            if archivos_cache_key in st.session_state.get('archivos_cache_persistente', {}):
                del st.session_state.archivos_cache_persistente[archivos_cache_key]

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