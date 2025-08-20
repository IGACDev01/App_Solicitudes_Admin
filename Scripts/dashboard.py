import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
from utils import invalidar_y_actualizar_cache
from timezone_utils_admin import obtener_fecha_actual_colombia, convertir_a_colombia, formatear_fecha_colombia


def mostrar_login_dashboard():
    """Interfaz de login para acceso al dashboard"""
    st.markdown("### 🔐 Acceso al Dashboard")
    
    with st.form("dashboard_login"):
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            usuario = st.text_input("Usuario:", key="usuario_dashboard_login")
            password = st.text_input("Contraseña:", type="password", key="password_dashboard_login")
            
            submitted = st.form_submit_button("🔓 Acceder al Dashboard", use_container_width=True)
            
            if submitted:
                if autenticar_dashboard(usuario, password):
                    st.session_state.dashboard_autenticado = True
                    st.session_state.usuario_dashboard = usuario
                    st.success(f"✅ Bienvenido al Dashboard, {usuario}")
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas")

def autenticar_dashboard(usuario, password):
    """Autenticar credenciales del dashboard - un solo nivel de administrador"""
    return usuario == "Admin_IGAC_2025" and password == "Solicitudes*5623"

def formatear_tiempo_dashboard(dias):
    """Formatear tiempo en días para el dashboard"""
    if pd.isna(dias) or dias == 0:
        return "N/A"
    
    if dias < 1:
        horas = dias * 24
        if horas < 1:
            minutos = horas * 60
            return f"{minutos:.0f}min"
        else:
            return f"{horas:.1f}h"
    elif dias < 2:
        return f"{dias:.1f} día"
    else:
        return f"{dias:.1f} días"

def operacion_datetime_segura(serie_dt, operacion='max'):
    """Realizar operaciones datetime de manera segura en Series"""
    try:
        if serie_dt.empty or serie_dt.isna().all():
            return None
        
        # Convertir a datetime y normalizar zona horaria usando utilidad
        dt_limpio = pd.to_datetime(serie_dt, errors='coerce')
        dt_limpio = dt_limpio.apply(convertir_a_colombia)
        dt_limpio = dt_limpio.dropna()
        
        if dt_limpio.empty:
            return None
            
        if operacion == 'max':
            return dt_limpio.max()
        elif operacion == 'min':
            return dt_limpio.min()
        else:
            return dt_limpio
    except Exception as e:
        print(f"Error en operación datetime: {e}")
        return None

def mostrar_tab_dashboard(gestor_datos):
    """Mostrar el tab del dashboard - optimizado para SharePoint con login simple"""
    
    # Verificar autenticación primero
    if not st.session_state.get('dashboard_autenticado', False):
        mostrar_login_dashboard()
        return
    
    # Estado de SharePoint
    estado = gestor_datos.obtener_estado_sharepoint()
    if not estado['sharepoint_conectado']:
        st.error("❌ Error de conexión con SharePoint Lists")
        return
    
    # Obtener todos los datos primero - ANTES de aplicar filtros
    df_todos = gestor_datos.obtener_todas_solicitudes()
    
    # Verificar si tenemos datos
    if df_todos.empty:
        st.info("📋 No hay solicitudes registradas aún. ¡Registre la primera solicitud en la pestaña de Registro!")
        return

    # Header con opción de cerrar sesión
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.header("📊 Dashboard de Solicitudes")
        usuario_actual = st.session_state.get('usuario_dashboard', 'Usuario')
        st.caption(f"👤 Sesión activa: {usuario_actual}")
    
    with col2:
        None

    with col3:
        if st.button("Cerrar Sesión", key="cerrar_sesion_dashboard"):
            st.session_state.dashboard_autenticado = False
            st.session_state.usuario_dashboard = None
            st.rerun()

    st.markdown(" ")

    if st.button("🔄 Actualizar Datos", key="actualizar_dashboard"):
        invalidar_y_actualizar_cache()
        st.rerun()
    
    st.markdown("---")

    # Inicializar o incrementar versión de filtro para claves de widgets
    if 'version_filtro' not in st.session_state:
        st.session_state.version_filtro = 0

    col1, col2, col3 = st.columns([2, 3, 1])

    with col1:
        # Obtener áreas únicas
        areas_disponibles = ["Todas"] + sorted(df_todos['area'].dropna().unique().tolist())
        
        filtro_area_global = st.selectbox(
            "Filtrar por Área:",
            options=areas_disponibles,
            index=0,  # Siempre empezar con "Todas"
            key=f"filtro_area_global_dashboard_{st.session_state.version_filtro}"
        )

    with col2:
        # Obtener procesos únicos
        procesos_disponibles = ["Todos"] + sorted(df_todos['proceso'].dropna().unique().tolist())
        
        filtro_proceso_global = st.selectbox(
            "Filtrar por Proceso:",
            options=procesos_disponibles,
            index=0,  # Siempre empezar con "Todos"
            key=f"filtro_proceso_global_dashboard_{st.session_state.version_filtro}"
        )

    with col3:
        # Botón limpiar filtros
        if st.button("🔄 Limpiar Filtros", key="limpiar_filtros_globales"):
            # Incrementar versión para crear nuevas instancias de widgets
            st.session_state.version_filtro += 1
            st.rerun()

    # Aplicar filtros globales a los datos
    df_filtrado_global = df_todos.copy()
    if filtro_area_global != "Todas":
        df_filtrado_global = df_filtrado_global[df_filtrado_global['area'] == filtro_area_global]
    if filtro_proceso_global != "Todos":
        df_filtrado_global = df_filtrado_global[df_filtrado_global['proceso'] == filtro_proceso_global]

    # Mostrar resultados filtrados
    if not df_filtrado_global.empty:
        st.info(f"📊 Mostrando {len(df_filtrado_global)} de {len(df_todos)} solicitudes")
    else:
        st.warning("⚠️ No se encontraron solicitudes con los filtros aplicados")
        return

    # Guardar datos originales
    df_original = gestor_datos.df
    
    # Establecer datos filtrados
    gestor_datos.df = df_filtrado_global
    
    # Obtener resumen de datos filtrados
    resumen = gestor_datos.obtener_resumen_solicitudes()
    
    # Mostrar hora de última actualización
    ultima_actualizacion = obtener_fecha_actual_colombia().strftime('%H:%M:%S')
    st.caption(f"📊 Última actualización: {ultima_actualizacion}")
    
    # Mostrar alertas del sistema
    mostrar_alertas_sistema(gestor_datos)
    
    # Métricas principales
    st.subheader("📈 Métricas Principales")
    mostrar_metricas_principales(gestor_datos)
       
    st.markdown("---")
    
    # Análisis visual
    st.subheader("📊 Análisis General")
    
    # Primera fila de gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        mostrar_grafico_estados(resumen)
    
    with col2:
        mostrar_grafico_prioridades(gestor_datos)

    # Segunda fila de gráficos
    mostrar_grafico_procesos(gestor_datos)
    
    # Tercera fila de gráficos
    mostrar_grafico_tipos(resumen)
       
    # Cuarta fila de gráficos
    mostrar_grafico_territoriales(gestor_datos)
    
    st.markdown("---")
    
    # Análisis temporal
    mostrar_analisis_temporal(gestor_datos)
    
    st.markdown("---")
    
    # Visualizador de DataFrame
    mostrar_visualizador_dataframe(gestor_datos)
    
    # IMPORTANTE: Restaurar datos originales al final
    gestor_datos.df = df_original

def mostrar_visualizador_dataframe(gestor_datos):
    """Mostrar visualizador de DataFrame con filtros avanzados - optimizado para SharePoint"""
    st.subheader("🔍 Explorador de Datos")
    
    df = gestor_datos.obtener_todas_solicitudes()
    
    if df.empty:
        st.info("📋 No hay datos disponibles para visualizar")
        return
           
    # Filtros avanzados
    with st.expander("🔧 Filtros Avanzados", expanded=False):
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            # Filtrar por estado
            estados_disponibles = ["Todos"] + list(df['estado'].unique())
            filtro_estado = st.selectbox("Estado:", estados_disponibles)
            
            # Filtrar por territorial
            if 'territorial' in df.columns:
                territoriales_disponibles = ["Todas"] + list(df['territorial'].unique())
                filtro_territorial = st.selectbox("Territorial:", territoriales_disponibles)
            else:
                filtro_territorial = "Todas"
        
        with filter_col2:
            # Filtrar por proceso
            areas_disponibles = ["Todas"] + list(df['proceso'].unique()) if 'proceso' in df.columns else ["Todas"]
            filtro_area = st.selectbox("Proceso:", areas_disponibles)
            
            # Filtrar por prioridad
            if 'prioridad' in df.columns:
                prioridades_disponibles = ["Todas"] + list(df['prioridad'].unique())
                filtro_prioridad = st.selectbox("Prioridad:", prioridades_disponibles)
            else:
                filtro_prioridad = "Todas"
        
        with filter_col3:
            # Filtro de rango de fechas
            if 'fecha_solicitud' in df.columns:
                fecha_min_dt = operacion_datetime_segura(df['fecha_solicitud'], 'min')
                fecha_max_dt = operacion_datetime_segura(df['fecha_solicitud'], 'max')
                
                if fecha_min_dt and fecha_max_dt:
                    fecha_min = fecha_min_dt.date()
                    fecha_max = fecha_max_dt.date()
                    
                    fecha_desde = st.date_input("Desde:", value=fecha_min, min_value=fecha_min, max_value=fecha_max)
                    fecha_hasta = st.date_input("Hasta:", value=fecha_max, min_value=fecha_min, max_value=fecha_max)
                else:
                    fecha_desde = fecha_hasta = None
            else:
                fecha_desde = fecha_hasta = None
        
        # Búsqueda de texto
        busqueda_texto = st.text_input("🔍 Buscar en descripción o ID:", placeholder="Escriba aquí...")
    
    # Aplicar filtros
    df_filtrado = df.copy()
    
    # Aplicar filtros básicos
    if filtro_estado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['estado'] == filtro_estado]
    
    if filtro_territorial != "Todas" and 'territorial' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['territorial'] == filtro_territorial]
    
    if filtro_area != "Todas" and 'proceso' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['proceso'] == filtro_area]
    
    if filtro_prioridad != "Todas" and 'prioridad' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['prioridad'] == filtro_prioridad]
    
    # Aplicar filtros de fecha
    if fecha_desde and fecha_hasta and 'fecha_solicitud' in df_filtrado.columns:
        df_filtrado['fecha_solicitud_limpia'] = df_filtrado['fecha_solicitud'].apply(convertir_a_colombia)
        
        df_filtrado = df_filtrado[
            (df_filtrado['fecha_solicitud_limpia'].dt.date >= fecha_desde) &
            (df_filtrado['fecha_solicitud_limpia'].dt.date <= fecha_hasta)
        ]
        df_filtrado = df_filtrado.drop('fecha_solicitud_limpia', axis=1)
    
    # Aplicar búsqueda de texto
    if busqueda_texto:
        mask = (
            df_filtrado['id_solicitud'].str.contains(busqueda_texto, case=False, na=False) |
            df_filtrado['descripcion'].str.contains(busqueda_texto, case=False, na=False) |
            df_filtrado['nombre_solicitante'].str.contains(busqueda_texto, case=False, na=False)
        )
        df_filtrado = df_filtrado[mask]
        
    if df_filtrado.empty:
        st.warning("⚠️ No se encontraron solicitudes con los filtros aplicados")
        return
    
    # Selección de columnas para mostrar
    with st.expander("📋 Seleccionar Columnas a Mostrar", expanded=False):
        columnas_disponibles = list(df_filtrado.columns)
        
        # Columnas importantes por defecto
        columnas_predeterminadas = [
            'id_solicitud', 'nombre_solicitante', 'estado', 'tipo_solicitud',
            'fecha_solicitud', 'territorial', 'proceso', 'prioridad'
        ]
        
        # Filtrar columnas predeterminadas para incluir solo las que existen
        columnas_predeterminadas = [col for col in columnas_predeterminadas if col in columnas_disponibles]
        
        # Multi-select para columnas
        columnas_seleccionadas = st.multiselect(
            "Columnas a mostrar:",
            options=columnas_disponibles,
            default=columnas_predeterminadas,
            help="Seleccione las columnas que desea visualizar"
        )
        
        if not columnas_seleccionadas:
            columnas_seleccionadas = columnas_predeterminadas

    max_filas = st.selectbox("📏 Filas a mostrar", [10, 25, 50, 100, "Todas"], index=1)

    # Aplicar límite de filas
    if max_filas != "Todas":
        df_mostrar = df_filtrado[columnas_seleccionadas].head(max_filas)
    else:
        df_mostrar = df_filtrado[columnas_seleccionadas]
     
    # Formatear fechas para mejor visualización
    df_mostrar_formateado = df_mostrar.copy()
    
    # Manejar columnas datetime de manera segura
    for col in df_mostrar_formateado.columns:
        if 'fecha' in col.lower() and col in df_mostrar_formateado.columns:
            try:
                df_col = df_mostrar_formateado[col]
                if pd.api.types.is_datetime64_any_dtype(df_col):
                    # Formatear usando utilidad de zona horaria
                    df_mostrar_formateado[col] = df_col.apply(lambda x: formatear_fecha_colombia(x) if pd.notna(x) else "N/A")
            except Exception as e:
                print(f"Error formateando columna {col}: {e}")
                continue
    
    # Usar st.dataframe con características interactivas
    st.dataframe(
        df_mostrar_formateado,
        use_container_width=True,
        height=400,
        column_config={
            "id_solicitud": st.column_config.TextColumn("ID", width="small"),
            "estado": st.column_config.TextColumn("Estado", width="small"),
            "prioridad": st.column_config.TextColumn("Prioridad", width="small"),
            "tiempo_respuesta_dias": st.column_config.NumberColumn("T. Respuesta (días)", format="%.2f"),
            "tiempo_resolucion_dias": st.column_config.NumberColumn("T. Resolución (días)", format="%.2f"),
        }
    )

    # Mostrar contador de resultados filtrados
    st.info(f"📊 Mostrando {len(df_filtrado)} de {len(df)} solicitudes")

    # Estadísticas rápidas para datos filtrados
    if len(df_filtrado) > 0:
        st.markdown("---")
        st.markdown("### 📈 Estadísticas de Datos Filtrados")
        
        stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
        
        with stat_col1:
            st.metric("Total Filtrado", len(df_filtrado))
        
        with stat_col2:
            if 'estado' in df_filtrado.columns:
                estado_mas_comun = df_filtrado['estado'].mode().iloc[0] if not df_filtrado['estado'].empty else "N/A"
                st.metric("Estado Más Común", estado_mas_comun)
        
        with stat_col3:
            if 'tiempo_resolucion_dias' in df_filtrado.columns:
                completadas = df_filtrado[df_filtrado['estado'] == 'Completada']
                if not completadas.empty and 'tiempo_resolucion_dias' in completadas.columns:
                    tiempo_promedio = completadas['tiempo_resolucion_dias'].mean()
                    st.metric("Tiempo Prom. Resolución", f"{tiempo_promedio:.1f} días")
                else:
                    st.metric("Tiempo Prom. Resolución", "N/A")
        
        with stat_col4:
            if 'territorial' in df_filtrado.columns:
                territorial_mas_activa = df_filtrado['territorial'].mode().iloc[0] if not df_filtrado['territorial'].empty else "N/A"
                st.metric("Territorial Más Activa", territorial_mas_activa)

def mostrar_alertas_sistema(gestor_datos):
    """Mostrar alertas del sistema"""
    df = gestor_datos.obtener_todas_solicitudes()
    
    if df.empty:
        return
    
    alertas = []
    
    # Solicitudes antiguas sin actualizar (>7 días)
    fecha_limite = obtener_fecha_actual_colombia() - timedelta(days=7)
    if 'fecha_actualizacion' in df.columns:
        try:
            # Usar utilidad de zona horaria para comparación
            df['fecha_actualizacion_limpia'] = df['fecha_actualizacion'].apply(convertir_a_colombia)
            
            solicitudes_antiguas = df[
                (df['fecha_actualizacion_limpia'] < fecha_limite) & 
                (df['estado'] != 'Completada')
            ]
            
            if not solicitudes_antiguas.empty:
                alertas.append({
                    'tipo': 'warning',
                    'titulo': '⚠️ Solicitudes sin actualizar',
                    'mensaje': f'{len(solicitudes_antiguas)} solicitudes llevan más de 7 días sin actualización',
                    'detalle': list(solicitudes_antiguas['id_solicitud'].head(5))
                })
        except Exception as e:
            print(f"Error verificando solicitudes antiguas: {e}")
    
    # Solicitudes de alta prioridad asignadas
    if 'prioridad' in df.columns:
        alta_prioridad_asignadas = df[
            (df['prioridad'] == 'Alta') & 
            (df['estado'] == 'Asignada')
        ]
        if not alta_prioridad_asignadas.empty:
            alertas.append({
                'tipo': 'error',
                'titulo': '🔴 Alta prioridad asignada',
                'mensaje': f'{len(alta_prioridad_asignadas)} solicitudes de alta prioridad sin atender',
                'detalle': list(alta_prioridad_asignadas['id_solicitud'].head(5))
            })
    
    # Mostrar alertas
    if alertas:
        st.subheader("🚨 Alertas del Sistema")
        for alerta in alertas:
            if alerta['tipo'] == 'warning':
                st.warning(f"**{alerta['titulo']}**: {alerta['mensaje']}")
            elif alerta['tipo'] == 'error':
                st.error(f"**{alerta['titulo']}**: {alerta['mensaje']}")
        
def mostrar_metricas_principales(gestor_datos):
    """Mostrar métricas principales en 4 filas"""
    df = gestor_datos.obtener_todas_solicitudes()
    
    if df.empty:
        st.info("No hay datos disponibles")
        return
    
    # Calcular métricas
    total = len(df)
    activas = len(df[(df['estado'] == 'Asignada') | (df['estado'] == 'En Proceso')])
    incompletas = len(df[df['estado'] == 'Incompleta'])
    completadas = len(df[df['estado'] == 'Completada'])
    
    # Tiempos medianos
    tiempo_respuesta_mediano = df[df['tiempo_respuesta_dias'] > 0]['tiempo_respuesta_dias'].median()
    tiempo_resolucion_mediano = df[df['estado'] == 'Completada']['tiempo_resolucion_dias'].median()
    tiempo_pausa_mediano = df[df['tiempo_pausado_dias'] > 0]['tiempo_pausado_dias'].median()
    
    # Tasa de resolución
    tasa_resolucion = (completadas / total * 100) if total > 0 else 0
    
    # Procesos con mejor y peor tiempo de resolución
    tiempos_por_proceso = df[df['estado'] == 'Completada'].groupby('proceso')['tiempo_resolucion_dias'].median().sort_values()
    proceso_mas_rapido = tiempos_por_proceso.index[0] if not tiempos_por_proceso.empty else "N/A"
    proceso_mas_lento = tiempos_por_proceso.index[-1] if not tiempos_por_proceso.empty else "N/A"
     
        
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 Total Solicitudes", total, 
                   help="Cuenta todas las solicitudes sin importar su estado actual")
    
    with col2:
        st.metric("🔄 Solicitudes Activas", activas, 
                  help="Solicitudes asignadas y en Proceso")
        
    
    with col3:
        st.metric("🟠 Incompletas", incompletas,
                   help="Solicitudes en estado 'Incompleta' que requieren información adicional")
    
    with col4:
        st.metric("✅ Completadas", completadas,
                   help="Solicitudes que han llegado al estado 'Completado'")
    
    # Segunda fila
    col1, col2, col3 = st.columns(3)
    
    with col1:
        valor_respuesta = f"{tiempo_respuesta_mediano:.1f} días" if pd.notna(tiempo_respuesta_mediano) else "N/A"
        st.metric("⏱️ Tiempo Mediano Respuesta", valor_respuesta,
                   help="Mediana del tiempo entre 'Asignada' y 'En Proceso' (excluye valores en 0)")
    
    with col2:
        valor_resolucion = f"{tiempo_resolucion_mediano:.1f} días" if pd.notna(tiempo_resolucion_mediano) else "N/A"
        st.metric("🏁 Tiempo Mediano Resolución", valor_resolucion,
                   help="Mediana del tiempo entre creación y estado 'Completada' (descontando pausas)")
    
    with col3:
        valor_pausa = f"{tiempo_pausa_mediano:.1f} días" if pd.notna(tiempo_pausa_mediano) else "N/A"
        st.metric("⏸️ Tiempo Mediano Pausa", valor_pausa,
                   help="Mediana de días que las solicitudes han estado pausadas (solo solicitudes con pausas)")
    
    # Tercera fila
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📈 Tasa de Resolución", f"{tasa_resolucion:.1f}%",
                   help="(Solicitudes Completadas / Total de Solicitudes) × 100")
    
    with col2:
        st.metric("🚀 Proceso Más Rápido", proceso_mas_rapido,
                   help="Proceso con menor tiempo mediano de resolución")
    
    with col3:
        st.metric("🐌 Proceso Más Lento", proceso_mas_lento,
                   help="Proceso con mayor tiempo mediano de resolución")
    
def mostrar_grafico_estados(resumen):
    """Mostrar gráfico de distribución por estados"""
    
    datos_estados = resumen['solicitudes_por_estado']
    
    if datos_estados:
        # Colores personalizados para cada estado
        colores = {
            'Asignada': '#FAD358',
            'En Proceso': '#42A5F5',
            'Incompleta': '#FD894A',
            'Completada': '#66BB6A',
            'Cancelada': '#EF5350'
        }
        
        fig = go.Figure(data=[
            go.Pie(
                labels=list(datos_estados.keys()),
                values=list(datos_estados.values()),
                hole=0.4,
                marker=dict(colors=[colores.get(k, '#CCCCCC') for k in datos_estados.keys()]),
                textinfo='label+percent',
                textposition='outside',
                hovertemplate='<b>%{label}</b><br>Cantidad: %{value}<br>Porcentaje: %{percent}<extra></extra>'
            )
        ])
        
        fig.update_layout(
            title="Distribución por Estado",
            height=350,
            showlegend=True,
            margin=dict(t=50, b=0, l=0, r=0),
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos disponibles")

def mostrar_grafico_tipos(resumen):
    """Mostrar gráfico de solicitudes por tipo (excluyendo 'Otro')"""
    
    datos_tipos = resumen['solicitudes_por_tipo']
    
    if datos_tipos:
        # Filtrar "Otro" antes de ordenar
        tipos_filtrados = {k: v for k, v in datos_tipos.items() if k != "Otro"}
        
        # Tomar solo los top 8 para mejor visualización (después de filtrar)
        tipos_ordenados = dict(sorted(tipos_filtrados.items(), key=lambda x: x[1], reverse=True)[:8])
        
        if tipos_ordenados:  # Verificar que hay datos después del filtro
            fig = px.bar(
                x=list(tipos_ordenados.values()),
                y=list(tipos_ordenados.keys()),
                orientation='h',
                color=list(tipos_ordenados.values()),
                color_continuous_scale='Viridis'
            )
            
            fig.update_layout(
                title="Solicitudes por Tipo",
                height=350, 
                margin=dict(t=50, b=0, l=0, r=0),
                showlegend=False,
                yaxis=dict(title=""),
                xaxis=dict(title="Cantidad",
                           tickmode='linear',
                            dtick=1),
                coloraxis_showscale=False
            )
            
            fig.update_traces(
                hovertemplate='<b>%{y}</b><br>Cantidad: %{x}<extra></extra>'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos específicos disponibles (solo categoría 'Otro')")
    else:
        st.info("No hay datos disponibles")

def mostrar_grafico_prioridades(gestor_datos):
    """Mostrar gráfico de distribución por prioridades en orden específico"""
   
    df = gestor_datos.obtener_todas_solicitudes()
    
    if not df.empty and 'prioridad' in df.columns:
        # Definir el orden deseado
        orden_prioridades = ['Por definir', 'Baja', 'Media', 'Alta']
        
        # Obtener conteos y reindexar en el orden deseado
        datos_prioridades = df['prioridad'].value_counts()
        prioridades_ordenadas = datos_prioridades.reindex(orden_prioridades, fill_value=0)
        
        colores_prioridad = {
            'Alta': '#d32f2f',
            'Media': '#f57c00',
            'Baja': '#388e3c',
            'Por definir': '#9e9e9e'
        }
        
        fig = go.Figure(data=[
            go.Bar(
                x=prioridades_ordenadas.index,
                y=prioridades_ordenadas.values,
                marker_color=[colores_prioridad.get(p, '#CCCCCC') for p in prioridades_ordenadas.index],
                hovertemplate='<b>%{x}</b><br>Cantidad: %{y}<extra></extra>'
            )
        ])
        
        fig.update_layout(
            title="Distribución por Prioridad",
            height=350, 
            margin=dict(t=50, b=0, l=0, r=0),
            xaxis=dict(
                title="Prioridad",
                categoryorder='array',
                categoryarray=orden_prioridades
            ),
            yaxis=dict(title="Cantidad",
                       tickmode='linear',
                        dtick=1
                       )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos disponibles")

def mostrar_grafico_procesos(gestor_datos):
    """Mostrar análisis por proceso (nueva estructura)"""
  
    df = gestor_datos.obtener_todas_solicitudes()
    
    if not df.empty and 'proceso' in df.columns:
        # Obtener conteo de solicitudes por proceso
        datos_proceso = df['proceso'].value_counts().head(10)  # Top 10 procesos
        
        if not datos_proceso.empty:
            fig = px.bar(
                x=datos_proceso.values,
                y=datos_proceso.index,
                orientation='h',
                color=datos_proceso.values,
                color_continuous_scale='Blues'
            )
            
            fig.update_layout(
                title="Solicitudes por Proceso",
                height=350, 
                margin=dict(t=50, b=0, l=0, r=0),
                showlegend=False,
                yaxis=dict(title="Proceso"),
                xaxis=dict(title="Cantidad de Solicitudes",
                           tickmode='linear',
                           dtick=1
                           ),
                coloraxis_showscale=False
            )
            
            fig.update_traces(
                hovertemplate='<b>%{y}</b><br>Solicitudes: %{x}<extra></extra>'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Mostrar estadística adicional
            total_procesos = df['proceso'].nunique()
            st.caption(f"📊 Total de procesos con solicitudes: {total_procesos}")
        else:
            st.info("No hay datos disponibles")
    else:
        st.info("No hay datos disponibles por proceso")

def mostrar_grafico_territoriales(gestor_datos):
    """Mostrar gráfico de solicitudes por territorial"""
    df = gestor_datos.obtener_todas_solicitudes()
    
    if not df.empty and 'territorial' in df.columns:
        datos_territorial = df['territorial'].value_counts().head(15)  # Top 15 para mejor visualización
        
        fig = px.bar(
            x=datos_territorial.values,
            y=datos_territorial.index,
            orientation='h',
            color=datos_territorial.values,
            color_continuous_scale='Viridis'
        )
        
        fig.update_layout(
            title="Solicitudes por Territorial",
            height=350, 
            margin=dict(t=50, b=0, l=0, r=0),
            showlegend=False,
            yaxis=dict(title="Territorial"),
            xaxis=dict(title="Cantidad de Solicitudes",
                       tickmode='linear',
                        dtick=1),
            coloraxis_showscale=False
        )
        
        fig.update_traces(
            hovertemplate='<b>%{y}</b><br>Solicitudes: %{x}<extra></extra>'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Mostrar estadística adicional
        total_territoriales = df['territorial'].nunique()
        st.caption(f"📊 Total de territoriales con solicitudes: {total_territoriales}")
    else:
        st.info("No hay datos disponibles")

def mostrar_analisis_temporal(gestor_datos):
    """Mostrar análisis temporal"""
    st.subheader("📈 Análisis Temporal")
    
    df = gestor_datos.obtener_todas_solicitudes()
    
    if df.empty or 'fecha_solicitud' not in df.columns:
        st.info("No hay datos suficientes para el análisis temporal")
        return
    
    try:
        # Limpiar columna datetime usando utilidad de zona horaria
        df['fecha_solicitud_limpia'] = df['fecha_solicitud'].apply(convertir_a_colombia)
        
        # Remover información de zona horaria para evitar advertencias de pandas
        df['fecha_solicitud_naive'] = df['fecha_solicitud_limpia'].dt.tz_localize(None)
        
        # Selector para agrupar por estado o prioridad
        col1, col2 = st.columns([1, 3])
        
        with col1:
            agrupacion = st.selectbox(
                "Agrupar por:",
                options=["Estado", "Prioridad"],
                key="agrupacion_temporal"
            )

        with col2:
            periodo_temporal = st.selectbox(
                "Período:",
                options=["Día", "Mes", "Trimestre"],
                index=1,  # Por defecto "Mes"
                key="periodo_temporal"
            )
        
        # Suprimir advertencias de pandas para conversión de período
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            # Gráfico de solicitudes por período
            if agrupacion == "Estado":
                # Crear columna de período basada en selección
                if periodo_temporal == "Día":
                    df['periodo'] = df['fecha_solicitud_naive'].dt.to_period('D')
                    titulo_periodo = "Día"
                elif periodo_temporal == "Mes":
                    df['periodo'] = df['fecha_solicitud_naive'].dt.to_period('M')
                    titulo_periodo = "Mes"
                else:  # Trimestre
                    df['periodo'] = df['fecha_solicitud_naive'].dt.to_period('Q')
                    titulo_periodo = "Trimestre"
                
                # Agrupar por período y estado
                datos_temporales = df.groupby(['periodo', 'estado']).size().reset_index(name='count')
                datos_temporales['periodo_str'] = datos_temporales['periodo'].astype(str)
                
                # Colores para estados
                colores_estado = {
                    'Asignada': '#fad358',
                    'En Proceso': '#42A5F5',
                    'Incompleta': '#fd894a', 
                    'Completada': '#66BB6A',
                    'Cancelada': '#EF5350'
                }
                
                fig = px.bar(
                    datos_temporales,
                    x='periodo_str',
                    y='count',
                    color='estado',
                    title=f"Solicitudes por {titulo_periodo} (Agrupadas por Estado)",
                    labels={
                        'periodo_str': titulo_periodo,
                        'count': 'Número de Solicitudes',
                        'estado': 'Estado'
                    },
                    color_discrete_map=colores_estado
                )
                
            else:  # Prioridad
                if 'prioridad' not in df.columns:
                    st.info("No hay datos de prioridad disponibles")
                    return
                    
                if periodo_temporal == "Día":
                    df['periodo'] = df['fecha_solicitud_naive'].dt.to_period('D')
                    titulo_periodo = "Día"
                elif periodo_temporal == "Mes":
                    df['periodo'] = df['fecha_solicitud_naive'].dt.to_period('M')
                    titulo_periodo = "Mes"
                else:  # Trimestre
                    df['periodo'] = df['fecha_solicitud_naive'].dt.to_period('Q')
                    titulo_periodo = "Trimestre"
                
                # Agrupar por período y prioridad
                datos_temporales = df.groupby(['periodo', 'prioridad']).size().reset_index(name='count')
                datos_temporales['periodo_str'] = datos_temporales['periodo'].astype(str)
                
                # Colores para prioridades
                colores_prioridad = {
                    'Alta': '#d32f2f',
                    'Media': '#f57c00',
                    'Baja': '#388e3c',
                    'Por definir': '#9e9e9e'
                }
                
                fig = px.bar(
                    datos_temporales,
                    x='periodo_str',
                    y='count',
                    color='prioridad',
                    title=f"Solicitudes por {titulo_periodo} (Agrupadas por Prioridad)",
                    labels={
                        'periodo_str': titulo_periodo,
                        'count': 'Número de Solicitudes',
                        'prioridad': 'Prioridad'
                    },
                    color_discrete_map=colores_prioridad
                )
            
            fig.update_layout(
                height=400,
                margin=dict(t=50, b=0, l=0, r=0),
                xaxis=dict(title=""),
                yaxis=dict(title="Número de Solicitudes",
                           tickmode='linear', 
                           dtick=1   
                           ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Gráfico de tiempo promedio de resolución por período
            if 'tiempo_resolucion_dias' in df.columns:
                completadas = df[df['estado'] == 'Completada'].copy()
                if not completadas.empty:
                    # Usar misma selección de período para tiempo de resolución
                    if periodo_temporal == "Día":
                        completadas['periodo_resolucion'] = completadas['fecha_solicitud_naive'].dt.to_period('D')
                    elif periodo_temporal == "Mes":
                        completadas['periodo_resolucion'] = completadas['fecha_solicitud_naive'].dt.to_period('M')
                    else:  # Trimestre
                        completadas['periodo_resolucion'] = completadas['fecha_solicitud_naive'].dt.to_period('Q')
                    
                    tiempos_por_periodo = completadas.groupby('periodo_resolucion')['tiempo_resolucion_dias'].mean().reset_index()
                    tiempos_por_periodo['periodo_str'] = tiempos_por_periodo['periodo_resolucion'].astype(str)
                    tiempos_por_periodo['tiempo_resolucion_dias'] = tiempos_por_periodo['tiempo_resolucion_dias'].round(2)
                    
                    if len(tiempos_por_periodo) > 0:
                        fig_tiempo = px.line(
                            tiempos_por_periodo,
                            x='periodo_str',
                            y='tiempo_resolucion_dias',
                            title=f"Tiempo Promedio de Resolución por {titulo_periodo}",
                            markers=True,
                            labels={
                                'periodo_str': titulo_periodo,
                                'tiempo_resolucion_dias': 'Tiempo Promedio (días)'
                            }
                        )
                        
                        fig_tiempo.update_traces(
                            line=dict(color='#ff6b6b', width=3),
                            marker=dict(size=8, color='#4ecdc4')
                        )
                        
                        fig_tiempo.update_layout(
                            height=350,
                            margin=dict(t=50, b=0, l=0, r=0),
                            xaxis=dict(title=titulo_periodo),
                            yaxis=dict(title="Tiempo Promedio (días)")
                        )
                        
                        st.plotly_chart(fig_tiempo, use_container_width=True)
                        
                        # Mostrar tendencia
                        if len(tiempos_por_periodo) >= 2:
                            tendencia = tiempos_por_periodo['tiempo_resolucion_dias'].iloc[-1] - tiempos_por_periodo['tiempo_resolucion_dias'].iloc[-2]
                            col1, col2, col3 = st.columns(3)
                            
                            with col2:  # Centrar el mensaje
                                if tendencia < -0.5:
                                    st.success("📈 Tendencia positiva: Los tiempos están mejorando")
                                elif tendencia > 0.5:
                                    st.warning("📉 Tendencia negativa: Los tiempos están aumentando")
                                else:
                                    st.info("➡️ Tendencia estable: Los tiempos se mantienen constantes")
                    else:
                        st.info("No hay suficientes datos de resolución por período")
                else:
                    st.info("No hay solicitudes completadas para analizar tiempos de resolución")
                    
    except Exception as e:
        st.error(f"Error en análisis temporal: {e}")
        print(f"Error análisis temporal: {e}")