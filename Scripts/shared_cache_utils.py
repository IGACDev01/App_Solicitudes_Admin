"""
Utilidades de Caché Compartidas
================================

Módulo que consolida todas las funciones de gestión de caché de Streamlit
para la aplicación de administración. Proporciona mecanismos para invalidar
caché y forzar actualización de datos cuando sea necesario.

Funcionalidades principales:
- Invalidación de caché de datos (@st.cache_data)
- Sistema de claves de caché para forzar refrescos selectivos
- Limpieza automática de datos temporales de sesión
- Mantenimiento periódico para optimizar rendimiento

Cuándo usar cada función:
- invalidar_cache_datos(): Después de escribir datos a SharePoint
- forzar_actualizacion_cache(): Para forzar recarga en funciones específicas
- invalidar_y_actualizar_cache(): Actualización completa (invalidar + nueva clave)
- periodic_maintenance(): Llamar al inicio de la app para limpieza

Autor: Equipo IGAC
Fecha: 2024-2025
"""

import time
from typing import Optional
import streamlit as st


def invalidar_cache_datos():
    """
    Invalidar todos los datos en caché de Streamlit

    Limpia todas las funciones decoradas con @st.cache_data, forzando que
    se recalculen en la próxima llamada. Útil después de operaciones de
    escritura a SharePoint.

    Nota:
        - Solo afecta @st.cache_data, no @st.cache_resource
        - Debe llamarse SIEMPRE después de actualizar datos en SharePoint
        - No afecta st.session_state
    """
    try:
        st.cache_data.clear()
        print("✅ Cache de datos invalidado")
    except Exception as e:
        print(f"⚠️ Error invalidando cache: {e}")


def forzar_actualizacion_cache() -> str:
    """
    Forzar actualización de caché generando nueva clave única

    Crea una clave de caché basada en timestamp actual y la almacena en
    st.session_state. Funciones que usan esta clave como parámetro
    recalcularán automáticamente al detectar la nueva clave.

    Returns:
        str: Nueva clave de caché generada (formato: "refresh_{timestamp}")

    Ejemplo de uso:
        ```python
        @st.cache_data
        def cargar_datos(cache_key: str = "default"):
            # Esta función se recalcula cuando cache_key cambia
            return obtener_datos_sharepoint()

        # Para forzar recarga:
        nueva_clave = forzar_actualizacion_cache()
        datos = cargar_datos(nueva_clave)
        ```
    """
    try:
        # Generar clave única basada en timestamp Unix actual
        cache_key = f"refresh_{int(time.time())}"
        st.session_state['cache_key'] = cache_key
        print(f"✅ Cache key actualizada: {cache_key}")
        return cache_key
    except Exception as e:
        print(f"⚠️ Error actualizando cache key: {e}")
        return "default"


def obtener_cache_key() -> str:
    """
    Obtener clave de caché actual almacenada en session_state

    Recupera la clave de caché del estado de sesión. Si no existe,
    retorna "default". Esta función se usa junto con funciones cacheadas
    que aceptan un parámetro cache_key.

    Returns:
        str: Clave de caché actual o "default" si no existe

    Nota:
        Esta función se llama típicamente desde main_admin.py para
        pasar la clave a funciones cacheadas.
    """
    return st.session_state.get('cache_key', 'default')


def invalidar_y_actualizar_cache() -> str:
    """
    Función combinada: invalidar caché Y actualizar clave

    Realiza una renovación completa del sistema de caché:
    1. Limpia todo el caché de datos actual
    2. Genera y guarda una nueva clave de caché

    Esta es la forma más agresiva de forzar actualización de datos.

    Returns:
        str: Nueva clave de caché generada

    Cuándo usar:
        - Después de operaciones críticas de escritura
        - Cuando se necesita garantizar que TODOS los datos se recarguen
        - Al detectar inconsistencias de datos
    """
    try:
        invalidar_cache_datos()
        cache_key = forzar_actualizacion_cache()
        print("✅ Cache completamente renovado")
        return cache_key
    except Exception as e:
        print(f"⚠️ Error en renovación completa de cache: {e}")
        return "default"


def cleanup_old_session_data():
    """
    Limpiar datos temporales antiguos del estado de sesión

    Elimina variables temporales de st.session_state que ya no son necesarias,
    liberando memoria. Llamar periódicamente para mantener sesión limpia.

    Variables limpiadas:
        - search_results: Resultados de búsqueda temporales
        - previous_search: Búsqueda anterior guardada
        - temp_data: Datos temporales diversos
        - modal_open: Estados de modales abiertos
        - form_submitted: Flags de formularios enviados

    Nota:
        Esta función es segura de llamar incluso si las claves no existen.
        Solo reporta limpieza si efectivamente eliminó variables.
    """
    try:
        # Lista de claves temporales que pueden eliminarse sin problemas
        temp_keys = [
            'search_results',
            'previous_search',
            'temp_data',
            'modal_open',
            'form_submitted'
        ]

        removed_count = 0
        for key in temp_keys:
            if key in st.session_state:
                del st.session_state[key]
                removed_count += 1

        if removed_count > 0:
            print(f"🧹 Limpiadas {removed_count} variables temporales de sesión")

    except Exception as e:
        print(f"⚠️ Error limpiando datos de sesión: {e}")


def periodic_maintenance():
    """
    Ejecutar mantenimiento periódico de caché y estado de sesión

    Función de mantenimiento que debe llamarse al inicio de la aplicación
    o a intervalos regulares para mantener la salud del caché y liberar memoria.

    Operaciones realizadas:
        1. Limpieza de datos temporales de sesión
        2. Logging de estadísticas de caché (si debug_mode está activo)

    Nota:
        - Llamar desde main() al inicio de cada sesión
        - No invalida caché, solo limpia datos innecesarios
        - Es segura de llamar múltiples veces
    """
    try:
        # Limpiar datos de sesión antiguos
        cleanup_old_session_data()

        # Registrar estadísticas si modo debug está activo
        if st.session_state.get('debug_mode', False):
            print("📊 Mantenimiento de caché completado exitosamente")

    except Exception as e:
        print(f"⚠️ Error durante mantenimiento periódico: {e}")
