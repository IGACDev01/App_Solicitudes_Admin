import streamlit as st
import time
from typing import Optional

def invalidar_cache_datos():
    """Invalidar cache de datos después de operaciones de escritura"""
    try:
        st.cache_data.clear()
        print("✅ Cache de datos invalidado")
    except Exception as e:
        print(f"⚠️ Error invalidando cache: {e}")

def forzar_actualizacion_cache():
    """Forzar actualización de cache generando nueva cache key"""
    try:
        # Generate unique cache key to force refresh
        cache_key = f"refresh_{int(time.time())}"
        st.session_state['cache_key'] = cache_key
        print(f"✅ Cache key actualizada: {cache_key}")
        return cache_key
    except Exception as e:
        print(f"⚠️ Error actualizando cache key: {e}")
        return "default"

def obtener_cache_key() -> str:
    """Obtener la cache key actual o generar una por defecto"""
    return st.session_state.get('cache_key', 'default')

def invalidar_y_actualizar_cache():
    """Función combinada: invalidar cache y forzar actualización"""
    try:
        invalidar_cache_datos()
        cache_key = forzar_actualizacion_cache()
        print("✅ Cache completamente renovado")
        return cache_key
    except Exception as e:
        print(f"⚠️ Error en renovación completa de cache: {e}")
        return "default"


import pandas as pd
from typing import List, Dict, Any


def calcular_tiempo_pausa_solicitud_individual(solicitud) -> float:
    """Calcular tiempo de pausa total para una solicitud individual en tiempo real"""
    from timezone_utils_admin import obtener_fecha_actual_colombia, convertir_a_colombia

    tiempo_pausado_total = 0
    fecha_actual = obtener_fecha_actual_colombia()

    # Tiempo pausado acumulado previo
    tiempo_previo = solicitud.get('tiempo_pausado_dias', 0)
    if pd.notna(tiempo_previo):
        tiempo_pausado_total += tiempo_previo

    # Si está actualmente pausada, agregar tiempo actual
    if solicitud.get('estado') == 'Incompleta':
        fecha_pausa = solicitud.get('fecha_pausa')
        if fecha_pausa and pd.notna(fecha_pausa):
            fecha_pausa_norm = convertir_a_colombia(fecha_pausa)
            if fecha_pausa_norm:
                tiempo_pausa_actual = (fecha_actual - fecha_pausa_norm).total_seconds() / (24 * 3600)
                tiempo_pausado_total += tiempo_pausa_actual

    return tiempo_pausado_total


def calcular_tiempo_pausa_en_tiempo_real(df: pd.DataFrame) -> float:
    """Calcular tiempo de pausa mediano en tiempo real para todas las solicitudes"""
    tiempos_pausa = []

    for _, solicitud in df.iterrows():
        tiempo_pausado = calcular_tiempo_pausa_solicitud_individual(solicitud)
        if tiempo_pausado > 0:
            tiempos_pausa.append(tiempo_pausado)

    return pd.Series(tiempos_pausa).median() if tiempos_pausa else None


def calcular_incompletas_con_tiempo_real(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Calcular solicitudes incompletas con tiempo real de pausa"""
    from timezone_utils_admin import convertir_a_colombia

    df_incompletas = df[df['estado'] == 'Incompleta']
    incompletas_antiguas_data = []

    for _, row in df_incompletas.iterrows():
        tiempo_pausado_total = calcular_tiempo_pausa_solicitud_individual(row)

        if tiempo_pausado_total > 7:  # More than 7 days paused
            fecha_pausa = row.get('fecha_pausa')
            fecha_pausa_colombia = convertir_a_colombia(fecha_pausa) if fecha_pausa and pd.notna(fecha_pausa) else None

            incompletas_antiguas_data.append({
                'id_solicitud': row['id_solicitud'],
                'nombre_solicitante': row['nombre_solicitante'],
                'dias_pausada': int(tiempo_pausado_total),
                'fecha_pausa': fecha_pausa_colombia
            })

    return incompletas_antiguas_data


def aplicar_tiempos_pausa_tiempo_real_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Aplicar cálculos de tiempo de pausa en tiempo real a un DataFrame"""
    df_resultado = df.copy()

    if 'tiempo_pausado_dias' in df_resultado.columns:
        # Calculate real-time pause times
        df_resultado['tiempo_pausado_real'] = df_resultado.apply(
            lambda row: calcular_tiempo_pausa_solicitud_individual(row),
            axis=1
        )

        # Replace the original column with real-time values
        df_resultado['tiempo_pausado_dias'] = df_resultado['tiempo_pausado_real']
        df_resultado = df_resultado.drop(['tiempo_pausado_real'], axis=1)

    return df_resultado