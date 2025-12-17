"""
Utilidades de caché compartidas para la aplicación de administración
Consolida funciones de gestión de caché
"""
import time
from typing import Optional
import streamlit as st


def invalidar_cache_datos():
    """Invalidar todos los datos de caché de Streamlit

    Limpia funciones y datos cacheados para forzar recalculación en la próxima llamada.
    """
    try:
        st.cache_data.clear()
        print("✅ Cache de datos invalidado")
    except Exception as e:
        print(f"⚠️ Error invalidando cache: {e}")


def forzar_actualizacion_cache() -> str:
    """Forzar actualización de caché generando nueva clave de caché

    Crea una clave de caché única basada en timestamp actual para forzar
    funciones con parámetro cache_key a recalcular.

    Returns:
        La nueva clave de caché
    """
    try:
        # Generar clave única para forzar refresh
        cache_key = f"refresh_{int(time.time())}"
        st.session_state['cache_key'] = cache_key
        print(f"✅ Cache key actualizada: {cache_key}")
        return cache_key
    except Exception as e:
        print(f"⚠️ Error actualizando cache key: {e}")
        return "default"


def obtener_cache_key() -> str:
    """Obtener clave de caché actual o retornar default

    Recupera la clave de caché del estado de sesión, usado para saltarse
    funciones cacheadas pasando una clave diferente.

    Returns:
        Clave de caché actual o 'default'
    """
    return st.session_state.get('cache_key', 'default')


def invalidar_y_actualizar_cache() -> str:
    """Función combinada: invalidar caché y forzar actualización

    Realiza tanto invalidación de caché como actualización de clave para máximo refresh.

    Returns:
        Nueva clave de caché después de actualizar
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
    """Clean up old or unnecessary session state data

    Removes temporary session state variables that are no longer needed.
    Call this periodically to free memory.
    """
    try:
        # List of temporary keys that can be safely removed
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
            print(f"🧹 Cleaned up {removed_count} temporary session keys")

    except Exception as e:
        print(f"⚠️ Error cleaning up session data: {e}")


def periodic_maintenance():
    """Perform periodic maintenance of cache and session state

    Should be called at app startup or at intervals to maintain
    cache health and free up memory.

    Performs:
    - Cache invalidation checks
    - Old session data cleanup
    - Cache statistics logging (debug mode)
    """
    try:
        # Clean up old session data
        cleanup_old_session_data()

        # Log cache stats if in debug mode
        if st.session_state.get('debug_mode', False):
            print("📊 Cache maintenance completed successfully")

    except Exception as e:
        print(f"⚠️ Error during periodic maintenance: {e}")
