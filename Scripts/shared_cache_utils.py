"""
Shared cache utilities for both Admin and User apps
Consolidates cache management functions from both applications
"""
import time
from typing import Optional
import streamlit as st


def invalidar_cache_datos():
    """Invalidate all Streamlit cache data

    Clears cached functions and data to force recalculation on next call.

    Aliases: cleanup_streamlit_cache()
    """
    try:
        st.cache_data.clear()
        print("✅ Cache de datos invalidado")
    except Exception as e:
        print(f"⚠️ Error invalidando cache: {e}")


# Alias for user app compatibility
def cleanup_streamlit_cache():
    """Cleanup Streamlit cache (alias for admin function)"""
    invalidar_cache_datos()


def forzar_actualizacion_cache() -> str:
    """Force cache update by generating new cache key

    Creates a unique cache key based on current timestamp to force
    functions with cache_key parameter to recalculate.

    Returns:
        The new cache key string

    Aliases: update_cache_key()
    """
    try:
        # Generate unique cache key to force refresh
        cache_key = f"refresh_{int(time.time())}"
        st.session_state['cache_key'] = cache_key
        print(f"✅ Cache key actualizada: {cache_key}")
        return cache_key
    except Exception as e:
        print(f"⚠️ Error actualizando cache key: {e}")
        return "default"


# Alias for user app compatibility
def update_cache_key() -> str:
    """Update cache key (alias for admin function)"""
    return forzar_actualizacion_cache()


def obtener_cache_key() -> str:
    """Get current cache key or return default

    Retrieves the cache key from session state, used to bypass cached
    functions by passing a different key.

    Returns:
        Current cache key or 'default'

    Aliases: get_cache_key()
    """
    return st.session_state.get('cache_key', 'default')


# Alias for user app compatibility
def get_cache_key() -> str:
    """Get current cache key (alias for admin function)"""
    return obtener_cache_key()


def invalidar_y_actualizar_cache() -> str:
    """Combined function: invalidate cache and force update

    Performs both cache invalidation and key update for maximum cache refresh.

    Returns:
        New cache key after update

    Aliases: cleanup_and_update_cache()
    """
    try:
        invalidar_cache_datos()
        cache_key = forzar_actualizacion_cache()
        print("✅ Cache completamente renovado")
        return cache_key
    except Exception as e:
        print(f"⚠️ Error en renovación completa de cache: {e}")
        return "default"


# Alias for user app compatibility
def cleanup_and_update_cache() -> str:
    """Cleanup and update cache (alias for admin function)"""
    return invalidar_y_actualizar_cache()


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
