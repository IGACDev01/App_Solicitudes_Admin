import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta


def mostrar_login_dashboard():
    """Login interface for dashboard access"""
    st.markdown("### 🔐 Acceso al Dashboard")
    
    with st.form("dashboard_login"):
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            usuario = st.text_input("Usuario:", key="usuario_dashboard_login")
            password = st.text_input("Contraseña:", type="password", key="password_dashboard_login")
            
            submitted = st.form_submit_button("🔓 Acceder al Dashboard", use_container_width=True)
            
            if submitted:
                if autenticar_dashboard(usuario, password):
                    st.session_state.dashboard_authenticated = True
                    st.session_state.dashboard_usuario = usuario
                    st.success(f"✅ Bienvenido al Dashboard, {usuario}")
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas")
    
    # Show credentials
    with st.expander("💡 Credenciales de Acceso"):
        st.write("**Dashboard Admin:** `dashboard_admin` / `dashboard2025`")

def autenticar_dashboard(usuario, password):
    """Authenticate dashboard credentials - single admin level"""
    return usuario == "dashboard_admin" and password == "dashboard2025"

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

def safe_datetime_operation(dt_series, operation='max'):
    """Safely perform datetime operations on Series"""
    try:
        if dt_series.empty or dt_series.isna().all():
            return None
        
        # Convert to datetime if needed and remove timezone info
        dt_clean = pd.to_datetime(dt_series, errors='coerce')
        dt_clean = dt_clean.dt.tz_localize(None) if dt_clean.dt.tz is not None else dt_clean
        dt_clean = dt_clean.dropna()
        
        if dt_clean.empty:
            return None
            
        if operation == 'max':
            return dt_clean.max()
        elif operation == 'min':
            return dt_clean.min()
        else:
            return dt_clean
    except Exception as e:
        print(f"Error in datetime operation: {e}")
        return None

def mostrar_tab_dashboard(data_manager):
    """Mostrar el tab del dashboard - SharePoint optimized with simple login"""
    
    # Check authentication first
    if not st.session_state.get('dashboard_authenticated', False):
        mostrar_login_dashboard()
        return
    
    # Header with logout option
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.header("📊 Dashboard de Solicitudes")
        usuario_actual = st.session_state.get('dashboard_usuario', 'Usuario')
        st.caption(f"👤 Sesión activa: {usuario_actual}")
    
    with col2:
        if st.button("🔄 Actualizar Datos", key="refresh_dashboard"):
            data_manager.load_data(force_reload=True)
            st.rerun()
    
    with col3:
        if st.button("🚪 Cerrar Sesión", key="logout_dashboard"):
            st.session_state.dashboard_authenticated = False
            st.session_state.dashboard_usuario = None
            st.rerun()
    
    st.markdown("---")
    
    # Barra de control
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("**Panel de control y análisis de solicitudes**")
    
    with col2:
        auto_refresh = st.checkbox("🔄 Auto-actualizar", value=False, key="auto_refresh")
        if auto_refresh:
            data_manager.load_data(force_reload=True)
            st.rerun()
    
    # SharePoint status
    status = data_manager.get_sharepoint_status()
    if not status['sharepoint_connected']:
        st.error("❌ Error de conexión con SharePoint Lists")
        return
    
    st.markdown("---")
    st.subheader("🔧 Filtros Globales")

    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        # Get unique areas
        df_all = data_manager.get_all_requests()
        areas_disponibles = ["Todas"] + sorted(df_all['area'].dropna().unique().tolist()) if not df_all.empty else ["Todas"]
        
        filtro_area_global = st.selectbox(
            "Filtrar por Área:",
            options=areas_disponibles,
            key="filtro_area_global_dashboard"
        )

    with col2:
        # Get unique processes
        procesos_disponibles = ["Todos"] + sorted(df_all['proceso'].dropna().unique().tolist()) if not df_all.empty else ["Todos"]
        
        filtro_proceso_global = st.selectbox(
            "Filtrar por Proceso:",
            options=procesos_disponibles,
            key="filtro_proceso_global_dashboard"
        )

    with col3:
        # Clear filters button
        if st.button("🔄 Limpiar Filtros", key="clear_global_filters"):
            st.session_state.filtro_area_global_dashboard = "Todas"
            st.session_state.filtro_proceso_global_dashboard = "Todos"
            st.rerun()

    # Apply global filters to data
    df_filtrado_global = df_all.copy()
    if filtro_area_global != "Todas":
        df_filtrado_global = df_filtrado_global[df_filtrado_global['area'] == filtro_area_global]
    if filtro_proceso_global != "Todos":
        df_filtrado_global = df_filtrado_global[df_filtrado_global['proceso'] == filtro_proceso_global]

    # Update data manager with filtered data for all subsequent operations
    data_manager.df = df_filtrado_global

    # Show filtered results
    if not df_filtrado_global.empty:
        st.info(f"📊 Mostrando {len(df_filtrado_global)} de {len(df_all)} solicitudes")
    else:
        st.warning("⚠️ No se encontraron solicitudes con los filtros aplicados")
        return

    # Obtener resumen de datos
    if hasattr(data_manager, 'df') and data_manager.df is not None:
        resumen = data_manager.get_requests_summary()
    else:
        st.warning("No hay datos disponibles")
        return
    
    if resumen.get('total_solicitudes', 0) == 0:
        st.info("📋 No hay solicitudes registradas aún. ¡Registre la primera solicitud en la pestaña de Registro!")
        return
    
    # Show last update time
    last_update = datetime.now().strftime('%H:%M:%S')
    st.caption(f"📊 Última actualización: {last_update}")
    
    # Mostrar alertas del sistema
    mostrar_alertas_sistema(data_manager)
    
    # Métricas principales
    st.subheader("📈 Métricas Principales")
    mostrar_metricas_principales(resumen)

    # Métricas tiempo
    mostrar_metricas_tiempo(resumen)
    
    # Estadísticas adicionales
    mostrar_estadisticas_adicionales(resumen)
    
    st.markdown("---")
    
    # Análisis visual
    st.subheader("📊 Análisis General")
    
    # Primera fila de gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        mostrar_grafico_estados(resumen)
    
    with col2:
        mostrar_grafico_prioridades(data_manager)
    
    # Segunda fila de gráficos
    mostrar_grafico_tipos(resumen)
    
    # Tercera fila de gráficos
    mostrar_grafico_procesos(data_manager)
        
    # Cuarta fila de gráficos
    mostrar_grafico_territoriales(data_manager)
    
    st.markdown("---")
    
    # Análisis temporal
    mostrar_analisis_temporal(data_manager)
    
    st.markdown("---")
    
    # DataFrame Visualizer
    mostrar_dataframe_visualizer(data_manager)
    
def mostrar_dataframe_visualizer(data_manager):
    """Mostrar visualizador de DataFrame con filtros avanzados - SharePoint optimized"""
    st.subheader("🔍 Explorador de Datos")
    
    df = data_manager.get_all_requests()
    
    if df.empty:
        st.info("📋 No hay datos disponibles para visualizar")
        return
           
    # Advanced filters
    with st.expander("🔧 Filtros Avanzados", expanded=False):
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            # Filter by estado
            estados_disponibles = ["Todos"] + list(df['estado'].unique())
            estado_filtro = st.selectbox("Estado:", estados_disponibles)
            
            # Filter by territorial
            if 'territorial' in df.columns:
                territoriales_disponibles = ["Todas"] + list(df['territorial'].unique())
                territorial_filtro = st.selectbox("Territorial:", territoriales_disponibles)
            else:
                territorial_filtro = "Todas"
        
        with filter_col2:
            # Filter by proceso
            areas_disponibles = ["Todas"] + list(df['proceso'].unique()) if 'proceso' in df.columns else ["Todas"]
            area_filtro = st.selectbox("Proceso:", areas_disponibles)
            
            # Filter by prioridad
            if 'prioridad' in df.columns:
                prioridades_disponibles = ["Todas"] + list(df['prioridad'].unique())
                prioridad_filtro = st.selectbox("Prioridad:", prioridades_disponibles)
            else:
                prioridad_filtro = "Todas"
        
        with filter_col3:
            # Date range filter
            if 'fecha_solicitud' in df.columns:
                fecha_min_dt = safe_datetime_operation(df['fecha_solicitud'], 'min')
                fecha_max_dt = safe_datetime_operation(df['fecha_solicitud'], 'max')
                
                if fecha_min_dt and fecha_max_dt:
                    fecha_min = fecha_min_dt.date()
                    fecha_max = fecha_max_dt.date()
                    
                    fecha_desde = st.date_input("Desde:", value=fecha_min, min_value=fecha_min, max_value=fecha_max)
                    fecha_hasta = st.date_input("Hasta:", value=fecha_max, min_value=fecha_min, max_value=fecha_max)
                else:
                    fecha_desde = fecha_hasta = None
            else:
                fecha_desde = fecha_hasta = None
        
        # Text search
        busqueda_texto = st.text_input("🔍 Buscar en descripción o ID:", placeholder="Escriba aquí...")
    
    # Apply filters
    df_filtrado = df.copy()
    
    # Apply basic filters
    if estado_filtro != "Todos":
        df_filtrado = df_filtrado[df_filtrado['estado'] == estado_filtro]
    
    if territorial_filtro != "Todas" and 'territorial' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['territorial'] == territorial_filtro]
    
    if area_filtro != "Todas" and 'proceso' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['proceso'] == area_filtro]
    
    if prioridad_filtro != "Todas" and 'prioridad' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['prioridad'] == prioridad_filtro]
    
    # Apply date filters
    if fecha_desde and fecha_hasta and 'fecha_solicitud' in df_filtrado.columns:
        df_filtrado['fecha_solicitud_clean'] = pd.to_datetime(df_filtrado['fecha_solicitud'], errors='coerce')
        if df_filtrado['fecha_solicitud_clean'].dt.tz is not None:
            df_filtrado['fecha_solicitud_clean'] = df_filtrado['fecha_solicitud_clean'].dt.tz_localize(None)
        
        df_filtrado = df_filtrado[
            (df_filtrado['fecha_solicitud_clean'].dt.date >= fecha_desde) &
            (df_filtrado['fecha_solicitud_clean'].dt.date <= fecha_hasta)
        ]
        df_filtrado = df_filtrado.drop('fecha_solicitud_clean', axis=1)
    
    # Apply text search
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
    
    # Column selection for display
    with st.expander("📋 Seleccionar Columnas a Mostrar", expanded=False):
        available_columns = list(df_filtrado.columns)
        
        # Default important columns
        default_columns = [
            'id_solicitud', 'nombre_solicitante', 'estado', 'tipo_solicitud',
            'fecha_solicitud', 'territorial', 'proceso', 'prioridad'
        ]
        
        # Filter default columns to only include those that exist
        default_columns = [col for col in default_columns if col in available_columns]
        
        # Multi-select for columns
        selected_columns = st.multiselect(
            "Columnas a mostrar:",
            options=available_columns,
            default=default_columns,
            help="Seleccione las columnas que desea visualizar"
        )
        
        if not selected_columns:
            selected_columns = default_columns


    max_rows = st.selectbox("📏 Filas a mostrar", [10, 25, 50, 100, "Todas"], index=1)

    # Apply row limit
    if max_rows != "Todas":
        df_display = df_filtrado[selected_columns].head(max_rows)
    else:
        df_display = df_filtrado[selected_columns]
     
    # Format dates for better display
    df_display_formatted = df_display.copy()
    
    # Handle datetime columns safely
    for col in df_display_formatted.columns:
        if 'fecha' in col.lower() and col in df_display_formatted.columns:
            try:
                df_col = df_display_formatted[col]
                if pd.api.types.is_datetime64_any_dtype(df_col):
                    # Remove timezone info and format
                    df_col_clean = pd.to_datetime(df_col, errors='coerce')
                    if df_col_clean.dt.tz is not None:
                        df_col_clean = df_col_clean.dt.tz_localize(None)
                    df_display_formatted[col] = df_col_clean.dt.strftime('%d/%m/%Y %H:%M')
            except Exception as e:
                print(f"Error formatting column {col}: {e}")
                continue
    
    # Use st.dataframe with interactive features
    st.dataframe(
        df_display_formatted,
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

    # Show filtered results count
    st.info(f"📊 Mostrando {len(df_filtrado)} de {len(df)} solicitudes")

    # Quick stats for filtered data
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
                completadas = df_filtrado[df_filtrado['estado'] == 'Completado']
                if not completadas.empty and 'tiempo_resolucion_dias' in completadas.columns:
                    tiempo_promedio = completadas['tiempo_resolucion_dias'].mean()
                    st.metric("Tiempo Prom. Resolución", f"{tiempo_promedio:.1f} días")
                else:
                    st.metric("Tiempo Prom. Resolución", "N/A")
        
        with stat_col4:
            if 'territorial' in df_filtrado.columns:
                territorial_mas_activa = df_filtrado['territorial'].mode().iloc[0] if not df_filtrado['territorial'].empty else "N/A"
                st.metric("Territorial Más Activa", territorial_mas_activa)

def mostrar_alertas_sistema(data_manager):
    """Mostrar alertas del sistema - SharePoint optimized"""
    df = data_manager.get_all_requests()
    
    if df.empty:
        return
    
    alertas = []
    
    # Solicitudes antiguas sin actualizar (>7 días)
    fecha_limite = datetime.now() - timedelta(days=7)
    if 'fecha_actualizacion' in df.columns:
        try:
            # Clean datetime column
            df['fecha_actualizacion_clean'] = pd.to_datetime(df['fecha_actualizacion'], errors='coerce')
            if df['fecha_actualizacion_clean'].dt.tz is not None:
                df['fecha_actualizacion_clean'] = df['fecha_actualizacion_clean'].dt.tz_localize(None)
            
            solicitudes_antiguas = df[
                (df['fecha_actualizacion_clean'] < fecha_limite) & 
                (df['estado'] != 'Completado')
            ]
            
            if not solicitudes_antiguas.empty:
                alertas.append({
                    'tipo': 'warning',
                    'titulo': '⚠️ Solicitudes sin actualizar',
                    'mensaje': f'{len(solicitudes_antiguas)} solicitudes llevan más de 7 días sin actualización',
                    'detalle': list(solicitudes_antiguas['id_solicitud'].head(5))
                })
        except Exception as e:
            print(f"Error checking old requests: {e}")
    
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
        
def mostrar_metricas_principales(resumen):
    """Mostrar métricas principales en cards"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="📋 Total Solicitudes",
            value=resumen['total_solicitudes'],
            delta=None
        )
    
    with col2:
        st.metric(
            label="🔄 Solicitudes Activas",
            value=resumen['solicitudes_activas'],
            delta=None
        )
    
    with col3:
        st.metric(
            label="✅ Completadas",
            value=resumen['solicitudes_completadas'],
            delta=None
        )

def mostrar_metricas_tiempo(resumen):
    """Mostrar métricas principales en cards"""
    col1, col2, col3 = st.columns(3)
        
    with col1:
        tiempo_respuesta = resumen['tiempo_promedio_respuesta']
        valor_respuesta = formatear_tiempo_dashboard(tiempo_respuesta) if tiempo_respuesta > 0 else "N/A"
        st.metric(
            label="⏱️ Tiempo Prom. Respuesta",
            value=valor_respuesta,
            delta=None
        )
    
    with col2:
        tiempo_resolucion = resumen['tiempo_promedio_resolucion']
        valor_resolucion = formatear_tiempo_dashboard(tiempo_resolucion) if tiempo_resolucion > 0 else "N/A"
        st.metric(
            label="🏁 Tiempo Prom. Resolución",
            value=valor_resolucion,
            delta=None
        )
    
    with col3:
        pass

def mostrar_estadisticas_adicionales(resumen):
    """Mostrar estadísticas adicionales"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Tasa de resolución
        if resumen['total_solicitudes'] > 0:
            tasa_resolucion = (resumen['solicitudes_completadas'] / resumen['total_solicitudes']) * 100
            st.metric(
                label="📈 Tasa de Resolución",
                value=f"{tasa_resolucion:.1f}%",
                delta=None
            )
    
    with col2:
        # Eficiencia (basada en tiempo de resolución)
        tiempo_resolucion = resumen['tiempo_promedio_resolucion']
        if tiempo_resolucion > 0:
            if tiempo_resolucion <= 1:
                eficiencia = "Excelente"
            elif tiempo_resolucion <= 3:
                eficiencia = "Buena"
            elif tiempo_resolucion <= 7:
                eficiencia = "Regular"
            else:
                eficiencia = "Mejorable"
            
            st.metric(
                label="⚡ Eficiencia",
                value=eficiencia,
                delta=None
            )
    
    with col3:
        # Carga de trabajo
        carga = "Baja" if resumen['solicitudes_activas'] <= 5 else "Media" if resumen['solicitudes_activas'] <= 15 else "Alta"
        st.metric(
            label="📊 Carga de Trabajo",
            value=carga,
            delta=None
        )

def mostrar_grafico_estados(resumen):
    """Mostrar gráfico de distribución por estados"""
    
    estados_data = resumen['solicitudes_por_estado']
    
    if estados_data:
        # Colores personalizados para cada estado
        colores = {
            'Asignada': '#FFA726',
            'En Proceso': '#42A5F5', 
            'Completado': '#66BB6A',
            'Cancelado': '#EF5350'
        }
        
        fig = go.Figure(data=[
            go.Pie(
                labels=list(estados_data.keys()),
                values=list(estados_data.values()),
                hole=0.4,
                marker=dict(colors=[colores.get(k, '#CCCCCC') for k in estados_data.keys()]),
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
    
    tipos_data = resumen['solicitudes_por_tipo']
    
    if tipos_data:
        # Filtrar "Otro" antes de ordenar
        tipos_filtrados = {k: v for k, v in tipos_data.items() if k != "Otro"}
        
        # Tomar solo los top 8 para mejor visualización (después de filtrar)
        tipos_sorted = dict(sorted(tipos_filtrados.items(), key=lambda x: x[1], reverse=True)[:8])
        
        if tipos_sorted:  # Verificar que hay datos después del filtro
            fig = px.bar(
                x=list(tipos_sorted.values()),
                y=list(tipos_sorted.keys()),
                orientation='h',
                color=list(tipos_sorted.values()),
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

def mostrar_grafico_prioridades(data_manager):
    """Mostrar gráfico de distribución por prioridades en orden específico"""
   
    df = data_manager.get_all_requests()
    
    if not df.empty and 'prioridad' in df.columns:
        # Definir el orden deseado
        orden_prioridades = ['Por definir', 'Baja', 'Media', 'Alta']
        
        # Obtener conteos y reindexar en el orden deseado
        prioridades_data = df['prioridad'].value_counts()
        prioridades_ordenadas = prioridades_data.reindex(orden_prioridades, fill_value=0)
        
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

def mostrar_grafico_procesos(data_manager):
    """Mostrar análisis por proceso (nueva estructura)"""
  
    df = data_manager.get_all_requests()
    
    if not df.empty and 'proceso' in df.columns:
        # Obtener conteo de solicitudes por proceso
        proceso_data = df['proceso'].value_counts().head(10)  # Top 10 procesos
        
        if not proceso_data.empty:
            fig = px.bar(
                x=proceso_data.values,
                y=proceso_data.index,
                orientation='h',
                color=proceso_data.values,
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

def mostrar_grafico_territoriales(data_manager):
    """Mostrar gráfico de solicitudes por territorial"""
    df = data_manager.get_all_requests()
    
    if not df.empty and 'territorial' in df.columns:
        territorial_data = df['territorial'].value_counts().head(15)  # Top 15 para mejor visualización
        
        fig = px.bar(
            x=territorial_data.values,
            y=territorial_data.index,
            orientation='h',
            color=territorial_data.values,
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

def mostrar_analisis_temporal(data_manager):
    """Mostrar análisis temporal"""
    st.subheader("📈 Análisis Temporal")
    
    df = data_manager.get_all_requests()
    
    if df.empty or 'fecha_solicitud' not in df.columns:
        st.info("No hay datos suficientes para el análisis temporal")
        return
    
    try:
        # Clean datetime column
        df['fecha_solicitud_clean'] = pd.to_datetime(df['fecha_solicitud'], errors='coerce')
        if df['fecha_solicitud_clean'].dt.tz is not None:
            df['fecha_solicitud_clean'] = df['fecha_solicitud_clean'].dt.tz_localize(None)
        
        # Create month column
        df['mes_solicitud'] = df['fecha_solicitud_clean'].dt.to_period('M')
        
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
                index=1,  # Default to "Mes"
                key="periodo_temporal"
            )
        
        # Gráfico de solicitudes por mes
        if agrupacion == "Estado":
            # Create period column based on selection
            if periodo_temporal == "Día":
                df['periodo'] = df['fecha_solicitud_clean'].dt.to_period('D')
                titulo_periodo = "Día"
            elif periodo_temporal == "Mes":
                df['periodo'] = df['fecha_solicitud_clean'].dt.to_period('M')
                titulo_periodo = "Mes"
            else:  # Trimestre
                df['periodo'] = df['fecha_solicitud_clean'].dt.to_period('Q')
                titulo_periodo = "Trimestre"
            
            # Agrupar por período y estado
            datos_temporales = df.groupby(['periodo', 'estado']).size().reset_index(name='count')
            datos_temporales['periodo_str'] = datos_temporales['periodo'].astype(str)
            
            # Colores para estados
            colores_estado = {
                'Asignada': '#FFA726',
                'En Proceso': '#42A5F5', 
                'Completado': '#66BB6A',
                'Cancelado': '#EF5350'
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
                df['periodo'] = df['fecha_solicitud_clean'].dt.to_period('D')
                titulo_periodo = "Día"
            elif periodo_temporal == "Mes":
                df['periodo'] = df['fecha_solicitud_clean'].dt.to_period('M')
                titulo_periodo = "Mes"
            else:  # Trimestre
                df['periodo'] = df['fecha_solicitud_clean'].dt.to_period('Q')
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
        
        # Gráfico de tiempo promedio de resolución por mes
        if 'tiempo_resolucion_dias' in df.columns:
            completadas = df[df['estado'] == 'Completado'].copy()
            if not completadas.empty:
                # Use same period selection for resolution time
                if periodo_temporal == "Día":
                    completadas['periodo_resolucion'] = completadas['fecha_solicitud_clean'].dt.to_period('D')
                elif periodo_temporal == "Mes":
                    completadas['periodo_resolucion'] = completadas['fecha_solicitud_clean'].dt.to_period('M')
                else:  # Trimestre
                    completadas['periodo_resolucion'] = completadas['fecha_solicitud_clean'].dt.to_period('Q')
                
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
                        xaxis=dict(title="Mes"),
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
                    st.info("No hay suficientes datos de resolución por mes")
            else:
                st.info("No hay solicitudes completadas para analizar tiempos de resolución")
                
    except Exception as e:
        st.error(f"Error en análisis temporal: {e}")
        print(f"Temporal analysis error: {e}")