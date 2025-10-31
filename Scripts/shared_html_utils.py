"""
Shared HTML utilities for both Admin and User apps
Consolidates HTML cleaning and comment formatting functions
"""
import re
from html import unescape
from functools import lru_cache
from typing import Optional


@lru_cache(maxsize=128)
def clean_html_content(content: str) -> str:
    """Clean HTML content for display

    Removes HTML tags and decodes entities.
    Handles pandas Timestamp objects, strings, and None values.

    Args:
        content: HTML or plain text content to clean

    Returns:
        Cleaned text or "Sin contenido disponible" if empty

    Aliases: limpiar_contenido_html()
    """
    if not content or not isinstance(content, str):
        return "Sin contenido disponible"

    try:
        # First, decode HTML entities
        content_clean = unescape(content)

        # Remove all HTML tags but preserve the text content
        content_clean = re.sub(r'<[^>]+>', '', content_clean)

        # Clean up extra whitespace and newlines
        content_clean = re.sub(r'\s+', ' ', content_clean).strip()

        # If the result is empty or too short, show fallback
        if not content_clean or len(content_clean.strip()) < 3:
            return "Sin contenido disponible"

        return content_clean

    except Exception as e:
        print(f"⚠️ Error cleaning HTML content: {e}")
        return "Sin contenido disponible"


# Alias for admin app compatibility
limpiar_contenido_html = clean_html_content


def formatear_comentarios_para_display(comentarios: str, separador: str = '\n\n---\n\n') -> str:
    """Format comments for better display in the UI

    Parses timestamps and authors from comment strings like:
    "[DD/MM/YYYY HH:MM COT - Author]: Comment text"

    Args:
        comentarios: Raw comments string (may contain HTML)
        separador: String to use between formatted comments

    Returns:
        Formatted comments with markdown styling

    Aliases: formatear_comentarios_administrador_para_mostrar()
    """
    if not comentarios or not comentarios.strip():
        return "Sin comentarios"

    try:
        # Clean HTML content first
        comentarios_clean = clean_html_content(comentarios)

        # Split by double newlines (comment separators)
        comentarios_lista = comentarios_clean.split('\n\n')
        comentarios_html = []

        for comentario in comentarios_lista:
            if comentario.strip():
                # Parse timestamp and author if available
                if comentario.startswith('[') and ']:' in comentario:
                    try:
                        timestamp_autor = comentario.split(']:')[0] + ']'
                        texto = comentario.split(']:')[1].strip()
                        # Format with bold timestamp
                        comentarios_html.append(f"**{timestamp_autor}**\n{texto}")
                    except Exception as e:
                        print(f"⚠️ Error parsing comment: {e}")
                        comentarios_html.append(comentario)
                else:
                    comentarios_html.append(comentario)

        return separador.join(comentarios_html)

    except Exception as e:
        print(f"⚠️ Error formatting comments: {e}")
        return "Error procesando comentarios"


# Alias for admin app compatibility (with different default separator)
def formatear_comentarios_administrador_para_mostrar(comentarios: str) -> str:
    """Format comments for admin panel display

    Uses different separator than user app version.

    Aliases: formatear_comentarios_para_display()
    """
    return formatear_comentarios_para_display(comentarios, separador='\n\n')


def clean_html_cached(content: str) -> str:
    """Cached HTML cleaning with memory limits

    Same as clean_html_content but with docstring indicating it's from utils.py

    This is maintained for backward compatibility with code that imports
    clean_html_cached directly from utils.py

    Args:
        content: HTML or plain text content to clean

    Returns:
        Cleaned text
    """
    # Limit input size to prevent memory issues
    if len(content) > 10000:  # 10KB limit
        content = content[:10000] + "... (contenido truncado)"

    return clean_html_content(content)
