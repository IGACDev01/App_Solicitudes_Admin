import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from timezone_utils import get_colombia_time, get_colombia_time_string, format_colombia_datetime, convert_to_colombia_time, normalize_datetime_for_comparison


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
    """Safely perform datetime operations on Series - FIXED"""
    try:
        if dt_series.empty or dt_series.isna().all():
            return None
        
        # Normalize all datetimes to Colombia timezone (timezone-naive)
        dt_normalized = dt_series.apply(
            lambda x: normalize_datetime_for_comparison(x) if pd.notna(x) else None
        ).dropna()
        
        if dt_normalized.empty:
            return None
            
        if operation == 'max':
            return dt_normalized.max()
        elif operation == 'min':
            return dt_normalized.min()
        else:
            return dt_normalized
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
    
    # Obtener resumen de datos
    resumen = data_manager.get_requests_summary()
    
    if resumen.get('total_solicitudes', 0) == 0:
        st.info("📋 No hay solicitudes registradas aún. ¡Registre la primera solicitud en la pestaña de Registro!")
        return
    
    # Show last update time
    last_update = get_colombia_time_string('%H:%M:%S')
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
    col1, col2 = st.columns(2)
    
    with col1:
        mostrar_grafico_areas(data_manager)
    
    with col2:
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
    
    # Controls section
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("**Explora y filtra los datos de solicitudes**")
    
    with col2:
        show_raw_data = st.checkbox("📊 Mostrar datos", value=False)
    
    with col3:
        max_rows = st.selectbox("📏 Filas a mostrar", [10, 25, 50, 100, "Todas"], index=1)
    
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
                # Convert to Colombia timezone first
                df_dates = df['fecha_solicitud'].apply(
                    lambda x: convert_to_colombia_time(x).date() if pd.notna(x) else None
                ).dropna()
                
                if not df_dates.empty:
                    fecha_min = df_dates.min()
                    fecha_max = df_dates.max()
                    
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
        # Normalize all dates to Colombia timezone for filtering
        df_filtrado['fecha_solicitud_colombia_date'] = df_filtrado['fecha_solicitud'].apply(
            lambda x: normalize_datetime_for_comparison(x).date() if normalize_datetime_for_comparison(x) else None
        )
        
        df_filtrado = df_filtrado[
            (df_filtrado['fecha_solicitud_colombia_date'] >= fecha_desde) &
            (df_filtrado['fecha_solicitud_colombia_date'] <= fecha_hasta) &
            (df_filtrado['fecha_solicitud_colombia_date'].notna())
        ]
        df_filtrado = df_filtrado.drop('fecha_solicitud_colombia_date', axis=1)
    
    # Apply text search
    if busqueda_texto:
        mask = (
            df_filtrado['id_solicitud'].str.contains(busqueda_texto, case=False, na=False) |
            df_filtrado['descripcion'].str.contains(busqueda_texto, case=False, na=False) |
            df_filtrado['nombre_solicitante'].str.contains(busqueda_texto, case=False, na=False)
        )
        df_filtrado = df_filtrado[mask]
    
    # Show filtered results count
    st.info(f"📊 Mostrando {len(df_filtrado)} de {len(df)} solicitudes")
    
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
    
    # Apply row limit
    if max_rows != "Todas":
        df_display = df_filtrado[selected_columns].head(max_rows)
    else:
        df_display = df_filtrado[selected_columns]
    
    # Display options
    col1, col2 = st.columns([3, 1])
    
    with col1:
        display_mode = st.radio(
            "Modo de visualización:",
            ["📊 Tabla Interactiva", "📋 Datos Simples"],
            horizontal=True
        )
    
    with col2:
        if st.button("📥 Descargar CSV", help="Descargar datos filtrados"):
            csv = df_filtrado.to_csv(index=False)
            st.download_button(
                label="⬇️ Descargar",
                data=csv,
                file_name=f"solicitudes_filtradas_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
    
    # Display the data - FIXED datetime formatting
    if display_mode == "📊 Tabla Interactiva":
        # Format dates for better display
        df_display_formatted = df_display.copy()
        
        # Handle datetime columns safely
        for col in df_display_formatted.columns:
            if 'fecha' in col.lower() and col in df_display_formatted.columns:
                try:
                    df_display_formatted[col] = df_display_formatted[col].apply(
                        lambda x: format_colombia_datetime(x, '%d/%m/%Y %H:%M') if pd.notna(x) else ''
                    )
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
    else:
        # Simple table view
        st.table(df_display)
    
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
    
    # Solicitudes antiguas sin actualizar (>7 días) - FIXED datetime handling
    fecha_limite = get_colombia_time() - timedelta(days=7)
    if 'fecha_actualizacion' in df.columns:
        try:
            # Convert all dates to Colombia timezone for comparison
            df_copy = df.copy()
            df_copy['fecha_actualizacion_colombia'] = df_copy['fecha_actualizacion'].apply(
                lambda x: convert_to_colombia_time(x).replace(tzinfo=None) if pd.notna(x) else None
            )
            
            solicitudes_antiguas = df_copy[
                (df_copy['fecha_actualizacion_colombia'] < fecha_limite.replace(tzinfo=None)) & 
                (df_copy['estado'] != 'Completado')
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
    
    # Solicitudes de alta prioridad pendientes
    if 'prioridad' in df.columns:
        alta_prioridad_pendientes = df[
            (df['prioridad'] == 'Alta') & 
            (df['estado'] == 'Pendiente')
        ]
        if not alta_prioridad_pendientes.empty:
            alertas.append({
                'tipo': 'error',
                'titulo': '🔴 Alta prioridad pendiente',
                'mensaje': f'{len(alta_prioridad_pendientes)} solicitudes de alta prioridad sin atender',
                'detalle': list(alta_prioridad_pendientes['id_solicitud'].head(5))
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
            'Pendiente': '#FFA726',
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
                xaxis=dict(title="Cantidad"),
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
        orden_prioridades = ['Sin asignar', 'Baja', 'Media', 'Alta']
        
        # Obtener conteos y reindexar en el orden deseado
        prioridades_data = df['prioridad'].value_counts()
        prioridades_ordenadas = prioridades_data.reindex(orden_prioridades, fill_value=0)
        
        colores_prioridad = {
            'Alta': '#d32f2f',
            'Media': '#f57c00',
            'Baja': '#388e3c',
            'Sin asignar': '#9e9e9e'
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
            yaxis=dict(title="Cantidad")
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos disponibles")

def mostrar_grafico_areas(data_manager):
    """Mostrar análisis por área (nueva estructura)"""
    st.subheader("🏢 Análisis por Área")
    
    df = data_manager.get_all_requests()
    
    if not df.empty and 'area' in df.columns:
        # Obtener todas las áreas
        areas_disponibles = df['area'].unique()
        
        # Crear DataFrame para el análisis
        area_data = []
        for area in areas_disponibles:
            area_df = df[df['area'] == area]
            
            # Calcular tiempo promedio de resolución para esta área
            completadas_area = area_df[area_df['estado'] == 'Completado']
            tiempo_promedio_resolucion = 0
            if not completadas_area.empty and 'tiempo_resolucion_dias' in completadas_area.columns:
                tiempo_promedio_resolucion = completadas_area['tiempo_resolucion_dias'].mean()
            
            pendientes = len(area_df[area_df['estado'] == 'Pendiente'])
            en_proceso = len(area_df[area_df['estado'] == 'En Proceso'])
            completadas = len(area_df[area_df['estado'] == 'Completado'])
            canceladas = len(area_df[area_df['estado'] == 'Cancelado'])
            total = len(area_df)
            
            area_data.append({
                'Area': area,
                'Pendientes': pendientes,
                'En Proceso': en_proceso,
                'Completadas': completadas,
                'Canceladas': canceladas,
                'Total': total,
                'Tasa_Completadas': round((completadas / total * 100), 2),
                'Tiempo_Resolucion': round(tiempo_promedio_resolucion, 2),
                'Pct_Pendientes': round((pendientes / total * 100), 2),
                'Pct_En_Proceso': round((en_proceso / total * 100), 2),
                'Pct_Completadas': round((completadas / total * 100), 2),
                'Pct_Canceladas': round((canceladas / total * 100), 2)
            })
        
        df_analysis = pd.DataFrame(area_data)
        
        if not df_analysis.empty:
            # Ordenar por total de solicitudes (de mayor a menor)
            df_analysis = df_analysis.sort_values('Total', ascending=False)
            
            # Gráfico de barras apiladas por área
            fig_bar = go.Figure()
            
            # Colores para cada estado
            colores = {
                'Completadas': '#66BB6A',
                'En Proceso': '#42A5F5', 
                'Pendientes': '#FFA726',
                'Canceladas': '#EF5350'
            }
            
            # Agregar barras para cada estado
            estados = ['Completadas', 'En Proceso', 'Pendientes', 'Canceladas']
            for estado in estados:
                pct_col = f'Pct_{estado.replace(" ", "_")}'
                fig_bar.add_trace(go.Bar(
                    name=estado,
                    x=df_analysis['Area'],
                    y=df_analysis[estado],
                    marker_color=colores[estado],
                    hovertemplate='<b>%{x}</b><br>' + 
                                estado + ': %{y}<br>' +
                                'Porcentaje: %{customdata:.2f}%<br>' +
                                'Total área: ' + df_analysis['Total'].astype(str) + '<br>' +
                                '<extra></extra>',
                    customdata=df_analysis[pct_col]
                ))
            
            # Configuración del layout
            fig_bar.update_layout(
                title="Distribución de Estados por Área",
                barmode='stack',
                height=400,
                margin=dict(t=50, b=0, l=0, r=0),
                xaxis=dict(
                    title="Área", 
                    tickangle=45,
                    categoryorder='array',
                    categoryarray=df_analysis['Area'].tolist()
                ),
                yaxis=dict(title="Número de Solicitudes"),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No hay datos disponibles")
    else:
        st.info("No hay datos disponibles por área")

def mostrar_grafico_procesos(data_manager):
    """Mostrar análisis por proceso (nueva estructura)"""
    st.subheader("📋 Análisis por Proceso")
    
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
                xaxis=dict(title="Cantidad de Solicitudes"),
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
    st.subheader("🗾 Análisis por Territorial")
    
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
            xaxis=dict(title="Cantidad de Solicitudes"),
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
    """Mostrar análisis temporal - FIXED datetime handling"""
    st.subheader("📈 Análisis Temporal")
    
    df = data_manager.get_all_requests()
    
    if df.empty or 'fecha_solicitud' not in df.columns:
        st.info("No hay datos suficientes para el análisis temporal")
        return
    
    try:
        # Convert to Colombia timezone and create month column
        df_copy = df.copy()
        df_copy['fecha_solicitud_colombia'] = df_copy['fecha_solicitud'].apply(
            lambda x: normalize_datetime_for_comparison(x) if pd.notna(x) else None
        )
        
        # Create month column
        mask = df_copy['fecha_solicitud_colombia'].notna()
        if mask.any():
            df_copy.loc[mask, 'mes_solicitud'] = pd.to_datetime(df_copy.loc[mask, 'fecha_solicitud_colombia']).dt.to_period('M')
        
        # Selector para agrupar por estado o prioridad
        col1, col2 = st.columns([1, 3])
        
        with col1:
            agrupacion = st.selectbox(
                "Agrupar por:",
                options=["Estado", "Prioridad"],
                key="agrupacion_temporal"
            )
        
        # Gráfico de solicitudes por mes
        if agrupacion == "Estado":
            # Agrupar por mes y estado
            datos_temporales = df.groupby(['mes_solicitud', 'estado']).size().reset_index(name='count')
            datos_temporales['mes_str'] = datos_temporales['mes_solicitud'].astype(str)
            
            # Colores para estados
            colores_estado = {
                'Pendiente': '#FFA726',
                'En Proceso': '#42A5F5', 
                'Completado': '#66BB6A',
                'Cancelado': '#EF5350'
            }
            
            fig = px.bar(
                datos_temporales,
                x='mes_str',
                y='count',
                color='estado',
                title="Solicitudes por Mes (Agrupadas por Estado)",
                labels={
                    'mes_str': 'Mes',
                    'count': 'Número de Solicitudes',
                    'estado': 'Estado'
                },
                color_discrete_map=colores_estado
            )
            
        else:  # Prioridad
            if 'prioridad' not in df.columns:
                st.info("No hay datos de prioridad disponibles")
                return
                
            # Agrupar por mes y prioridad
            datos_temporales = df.groupby(['mes_solicitud', 'prioridad']).size().reset_index(name='count')
            datos_temporales['mes_str'] = datos_temporales['mes_solicitud'].astype(str)
            
            # Colores para prioridades
            colores_prioridad = {
                'Alta': '#d32f2f',
                'Media': '#f57c00',
                'Baja': '#388e3c',
                'Sin asignar': '#9e9e9e'
            }
            
            fig = px.bar(
                datos_temporales,
                x='mes_str',
                y='count',
                color='prioridad',
                title="Solicitudes por Mes (Agrupadas por Prioridad)",
                labels={
                    'mes_str': 'Mes',
                    'count': 'Número de Solicitudes',
                    'prioridad': 'Prioridad'
                },
                color_discrete_map=colores_prioridad
            )
        
        fig.update_layout(
            height=400,
            margin=dict(t=50, b=0, l=0, r=0),
            xaxis=dict(title="Mes"),
            yaxis=dict(title="Número de Solicitudes"),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Gráfico de tiempo promedio de resolución por mes - FIXED
        if 'tiempo_resolucion_dias' in df.columns:
            completadas = df_copy[df_copy['estado'] == 'Completado'].copy()
            if not completadas.empty:
                # Use fecha_completado if available, otherwise fecha_solicitud (both in Colombia timezone)
                if 'fecha_completado' in completadas.columns:
                    completadas['fecha_completado_colombia'] = completadas['fecha_completado'].apply(
                        lambda x: convert_to_colombia_time(x) if pd.notna(x) else None
                    )
                    completadas['mes_resolucion'] = completadas['fecha_completado_colombia'].dt.to_period('M')
                else:
                    completadas['mes_resolucion'] = completadas['fecha_solicitud_colombia'].dt.to_period('M')
                
                tiempos_por_mes = completadas.groupby('mes_resolucion')['tiempo_resolucion_dias'].mean().reset_index()
                tiempos_por_mes['mes_str'] = tiempos_por_mes['mes_resolucion'].astype(str)
                tiempos_por_mes['tiempo_resolucion_dias'] = tiempos_por_mes['tiempo_resolucion_dias'].round(2)
                
                if len(tiempos_por_mes) > 0:
                    fig_tiempo = px.line(
                        tiempos_por_mes,
                        x='mes_str',
                        y='tiempo_resolucion_dias',
                        title="Tiempo Promedio de Resolución por Mes",
                        markers=True,
                        labels={
                            'mes_str': 'Mes',
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
                    if len(tiempos_por_mes) >= 2:
                        tendencia = tiempos_por_mes['tiempo_resolucion_dias'].iloc[-1] - tiempos_por_mes['tiempo_resolucion_dias'].iloc[-2]
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