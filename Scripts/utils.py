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