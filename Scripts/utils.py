"""
Utilidades Generales
====================

Módulo que proporciona funciones auxiliares para cálculos relacionados con
tiempos de pausa de solicitudes en estado "Incompleta".

Funcionalidades principales:
- Cálculo de tiempo de pausa en tiempo real para solicitudes individuales
- Cálculo de tiempo de pausa mediano para datasets completos
- Identificación de solicitudes pausadas por más de 7 días
- Aplicación masiva de cálculos de pausa a DataFrames

Concepto de "tiempo de pausa en tiempo real":
    Las solicitudes en estado "Incompleta" acumulan tiempo de pausa. Este
    módulo calcula el tiempo total sumando:
    1. Tiempo pausado histórico (pausas anteriores ya completadas)
    2. Tiempo de la pausa actual (si está actualmente en estado Incompleta)

Uso típico:
    ```python
    from utils import calcular_tiempo_pausa_solicitud_individual

    # Para una solicitud individual
    tiempo_pausado = calcular_tiempo_pausa_solicitud_individual(solicitud)

    # Para identificar solicitudes con pausas largas
    incompletas_antiguas = calcular_incompletas_con_tiempo_real(df)
    ```

Autor: Equipo IGAC
Fecha: 2024-2025
"""

import streamlit as st
from typing import Optional
from shared_cache_utils import invalidar_cache_datos, invalidar_y_actualizar_cache, obtener_cache_key

import pandas as pd
from typing import List, Dict, Any


def calcular_tiempo_pausa_solicitud_individual(solicitud) -> float:
    """
    Calcular tiempo de pausa total en tiempo real para una solicitud individual

    Calcula el tiempo total que una solicitud ha estado pausada (en estado Incompleta),
    incluyendo tanto pausas históricas completadas como la pausa actual si está activa.

    Args:
        solicitud: Fila de DataFrame (Series) o diccionario con datos de solicitud.
                  Campos requeridos:
                  - 'tiempo_pausado_dias': Tiempo pausado histórico acumulado
                  - 'estado': Estado actual de la solicitud
                  - 'fecha_pausa': Fecha de inicio de la pausa actual (si aplica)

    Returns:
        float: Tiempo total pausado en días (con decimales para precisión de horas)

    Ejemplo:
        ```python
        # Solicitud pausada hace 3 días, con 2 días de pausas anteriores
        solicitud = {
            'estado': 'Incompleta',
            'tiempo_pausado_dias': 2.0,
            'fecha_pausa': datetime(2024, 12, 14, 10, 0, 0)  # Hace 3 días
        }
        tiempo_total = calcular_tiempo_pausa_solicitud_individual(solicitud)
        # Resultado: 5.0 días (2 históricos + 3 actuales)
        ```

    Nota:
        - Si la solicitud NO está en estado 'Incompleta', solo cuenta tiempo histórico
        - Si fecha_pausa es None o NaN, solo cuenta tiempo histórico
        - Usa hora de Colombia (COT) para cálculos de diferencia temporal
        - Precisión: segundos convertidos a días (segundos / 86400)
    """
    from shared_timezone_utils import obtener_fecha_actual_colombia, convertir_a_colombia

    tiempo_pausado_total = 0
    fecha_actual = obtener_fecha_actual_colombia()

    # Paso 1: Agregar tiempo pausado acumulado de pausas anteriores
    tiempo_previo = solicitud.get('tiempo_pausado_dias', 0)
    if pd.notna(tiempo_previo):
        tiempo_pausado_total += tiempo_previo

    # Paso 2: Si está actualmente pausada, agregar tiempo de pausa actual
    if solicitud.get('estado') == 'Incompleta':
        fecha_pausa = solicitud.get('fecha_pausa')
        if fecha_pausa and pd.notna(fecha_pausa):
            # Convertir fecha de pausa a hora Colombia
            fecha_pausa_norm = convertir_a_colombia(fecha_pausa)
            if fecha_pausa_norm:
                # Calcular diferencia en días (con decimales)
                tiempo_pausa_actual = (fecha_actual - fecha_pausa_norm).total_seconds() / (24 * 3600)
                tiempo_pausado_total += tiempo_pausa_actual

    return tiempo_pausado_total


def calcular_tiempo_pausa_en_tiempo_real(df: pd.DataFrame) -> float:
    """
    Calcular tiempo de pausa mediano en tiempo real para todas las solicitudes

    Calcula la mediana de tiempos de pausa para todas las solicitudes que tienen
    tiempo de pausa mayor a 0. Útil para métricas generales del dashboard.

    Args:
        df (pd.DataFrame): DataFrame con solicitudes

    Returns:
        float: Mediana de tiempos de pausa en días, o None si no hay pausas

    Ejemplo:
        ```python
        # DataFrame con varias solicitudes
        mediana_pausa = calcular_tiempo_pausa_en_tiempo_real(df)
        # Resultado: 3.5 días (mediana de todas las pausas)
        ```

    Nota:
        - Solo considera solicitudes con tiempo_pausado > 0
        - Retorna None si no hay solicitudes pausadas
        - Usa mediana en lugar de promedio para evitar outliers
        - Calcula tiempo real (incluye pausas activas)
    """
    tiempos_pausa = []

    # Iterar sobre todas las solicitudes y calcular tiempo de pausa
    for _, solicitud in df.iterrows():
        tiempo_pausado = calcular_tiempo_pausa_solicitud_individual(solicitud)
        if tiempo_pausado > 0:
            tiempos_pausa.append(tiempo_pausado)

    # Retornar mediana si hay datos, None si no hay solicitudes pausadas
    return pd.Series(tiempos_pausa).median() if tiempos_pausa else None


def calcular_incompletas_con_tiempo_real(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Calcular solicitudes incompletas con tiempo real de pausa mayor a 7 días

    Identifica solicitudes que llevan más de 7 días pausadas (en estado Incompleta)
    y retorna sus detalles para alertas o reportes.

    Args:
        df (pd.DataFrame): DataFrame con todas las solicitudes

    Returns:
        List[Dict[str, Any]]: Lista de diccionarios con solicitudes pausadas >7 días
                             Cada diccionario contiene:
                             - 'id_solicitud': ID de la solicitud
                             - 'nombre_solicitante': Nombre del solicitante
                             - 'dias_pausada': Días totales pausada (entero)
                             - 'fecha_pausa': Fecha inicio de pausa (hora Colombia)

    Ejemplo:
        ```python
        incompletas = calcular_incompletas_con_tiempo_real(df)
        # Resultado:
        # [
        #   {
        #     'id_solicitud': 'SOL-001',
        #     'nombre_solicitante': 'Juan Pérez',
        #     'dias_pausada': 10,
        #     'fecha_pausa': datetime(2024, 12, 7, 10, 0, 0)
        #   },
        #   ...
        # ]
        ```

    Nota:
        - Umbral fijo de 7 días (modificar si se requiere diferente)
        - Solo considera solicitudes en estado 'Incompleta'
        - Fechas convertidas a hora Colombia (COT)
        - Días redondeados a entero para presentación
    """
    from shared_timezone_utils import convertir_a_colombia

    # Filtrar solo solicitudes en estado Incompleta
    df_incompletas = df[df['estado'] == 'Incompleta']
    incompletas_antiguas_data = []

    for _, row in df_incompletas.iterrows():
        # Calcular tiempo total pausado (histórico + actual)
        tiempo_pausado_total = calcular_tiempo_pausa_solicitud_individual(row)

        # Si supera el umbral de 7 días, agregar a la lista
        if tiempo_pausado_total > 7:
            fecha_pausa = row.get('fecha_pausa')
            fecha_pausa_colombia = convertir_a_colombia(fecha_pausa) if fecha_pausa and pd.notna(fecha_pausa) else None

            incompletas_antiguas_data.append({
                'id_solicitud': row['id_solicitud'],
                'nombre_solicitante': row['nombre_solicitante'],
                'dias_pausada': int(tiempo_pausado_total),  # Redondear a entero
                'fecha_pausa': fecha_pausa_colombia
            })

    return incompletas_antiguas_data


def aplicar_tiempos_pausa_tiempo_real_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplicar cálculos de tiempo de pausa en tiempo real a todo un DataFrame

    Actualiza la columna 'tiempo_pausado_dias' en el DataFrame con valores
    calculados en tiempo real (incluyendo pausas activas).

    Args:
        df (pd.DataFrame): DataFrame con solicitudes

    Returns:
        pd.DataFrame: Nuevo DataFrame con tiempos de pausa actualizados en tiempo real

    Ejemplo:
        ```python
        # DataFrame original con tiempos históricos
        df_original = obtener_solicitudes()

        # Actualizar con tiempos en tiempo real
        df_actualizado = aplicar_tiempos_pausa_tiempo_real_dataframe(df_original)

        # Ahora df_actualizado tiene tiempos de pausa actualizados
        # incluyendo pausas actualmente en curso
        ```

    Nota:
        - Crea una copia del DataFrame (no modifica el original)
        - Solo procesa si existe la columna 'tiempo_pausado_dias'
        - Reemplaza valores históricos con valores en tiempo real
        - Usa apply() para iterar eficientemente sobre filas
        - Elimina columna temporal después del cálculo

    Flujo interno:
        1. Crear copia del DataFrame
        2. Calcular columna temporal 'tiempo_pausado_real'
        3. Reemplazar 'tiempo_pausado_dias' con valores en tiempo real
        4. Eliminar columna temporal
        5. Retornar DataFrame actualizado
    """
    df_resultado = df.copy()

    # Solo procesar si existe la columna de tiempo pausado
    if 'tiempo_pausado_dias' in df_resultado.columns:
        # Calcular tiempos de pausa en tiempo real para cada fila
        df_resultado['tiempo_pausado_real'] = df_resultado.apply(
            lambda row: calcular_tiempo_pausa_solicitud_individual(row),
            axis=1
        )

        # Reemplazar columna original con valores en tiempo real
        df_resultado['tiempo_pausado_dias'] = df_resultado['tiempo_pausado_real']

        # Eliminar columna temporal
        df_resultado = df_resultado.drop(['tiempo_pausado_real'], axis=1)

    return df_resultado
