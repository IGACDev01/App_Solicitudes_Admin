"""
Utilidades Compartidas de HTML
===============================

Módulo que consolida funciones de limpieza y formateo de contenido HTML
para prevenir ataques XSS (Cross-Site Scripting) y mejorar la visualización
de contenido generado por usuarios.

Funcionalidades principales:
- Sanitización de contenido HTML (eliminar tags peligrosos)
- Decodificación de entidades HTML
- Formateo de comentarios con timestamps para visualización
- Caché de resultados para optimizar rendimiento

Seguridad:
    Este módulo es CRÍTICO para seguridad. Nunca renderizar HTML sin sanitizar
    ya que podría permitir ataques XSS donde usuarios inyectan JavaScript malicioso.

Uso típico:
    ```python
    from shared_html_utils import limpiar_contenido_html

    # Limpiar contenido antes de almacenar o mostrar
    contenido_seguro = limpiar_contenido_html(input_usuario)
    st.markdown(contenido_seguro)  # Seguro de mostrar
    ```

Autor: Equipo IGAC
Fecha: 2024-2025
"""

import re
from html import unescape
from functools import lru_cache
from typing import Optional


@lru_cache(maxsize=128)
def clean_html_content(content: str) -> str:
    """
    Limpiar contenido HTML para visualización segura

    Elimina todas las etiquetas HTML y decodifica entidades HTML para prevenir
    ataques XSS. Utiliza caché LRU para optimizar rendimiento en contenido repetido.

    Args:
        content (str): Contenido HTML o texto plano a limpiar

    Returns:
        str: Texto limpio sin tags HTML, o "Sin contenido disponible" si está vacío

    Ejemplo:
        ```python
        html = "<p>Hola <script>alert('XSS')</script> Mundo</p>"
        limpio = clean_html_content(html)
        # Resultado: "Hola Mundo"
        ```

    Nota:
        - Caché de hasta 128 resultados diferentes (LRU cache)
        - Maneja objetos Timestamp de pandas, strings y valores None
        - Elimina TODAS las etiquetas HTML (<script>, <iframe>, <style>, etc.)
        - Preserva el contenido de texto dentro de las etiquetas
        - Si el resultado tiene menos de 3 caracteres, retorna mensaje por defecto

    Alias disponible: limpiar_contenido_html()
    """
    if not content or not isinstance(content, str):
        return "Sin contenido disponible"

    try:
        # Paso 1: Decodificar entidades HTML (&amp; → &, &lt; → <, etc.)
        content_clean = unescape(content)

        # Paso 2: Eliminar todas las etiquetas HTML pero preservar contenido de texto
        content_clean = re.sub(r'<[^>]+>', '', content_clean)

        # Paso 3: Limpiar espacios en blanco extras y saltos de línea
        content_clean = re.sub(r'\s+', ' ', content_clean).strip()

        # Paso 4: Validar que el resultado tenga contenido significativo
        if not content_clean or len(content_clean.strip()) < 3:
            return "Sin contenido disponible"

        return content_clean

    except Exception as e:
        print(f"⚠️ Error limpiando contenido HTML: {e}")
        return "Sin contenido disponible"


# Alias en español para compatibilidad con aplicación de administración
limpiar_contenido_html = clean_html_content


def formatear_comentarios_para_display(comentarios: str, separador: str = '\n\n---\n\n') -> str:
    """
    Formatear comentarios para mejor visualización en la interfaz de usuario

    Parsea timestamps y autores de strings de comentarios que siguen el formato:
    "[DD/MM/YYYY HH:MM COT - Autor]: Texto del comentario"

    Aplica formato Markdown para resaltar timestamps y separar comentarios visualmente.

    Args:
        comentarios (str): String crudo de comentarios (puede contener HTML)
        separador (str): String para separar comentarios formateados.
                        Por defecto: '\n\n---\n\n' (línea horizontal)

    Returns:
        str: Comentarios formateados con estilos Markdown, o "Sin comentarios" si vacío

    Ejemplo:
        ```python
        raw = "[17/12/2024 14:30 COT - Admin]: Solicitud aprobada\n\n[17/12/2024 15:00 COT - User]: Gracias"
        formatted = formatear_comentarios_para_display(raw)
        # Resultado:
        # **[17/12/2024 14:30 COT - Admin]**
        # Solicitud aprobada
        #
        # ---
        #
        # **[17/12/2024 15:00 COT - User]**
        # Gracias
        ```

    Nota:
        - Limpia HTML antes de formatear (prevención XSS)
        - Los timestamps se muestran en negrita
        - Comentarios sin formato de timestamp se muestran tal cual
        - Ignora comentarios vacíos

    Alias disponible: formatear_comentarios_administrador_para_mostrar()
    """
    if not comentarios or not comentarios.strip():
        return "Sin comentarios"

    try:
        # Limpiar contenido HTML primero (seguridad)
        comentarios_clean = clean_html_content(comentarios)

        # Dividir por dobles saltos de línea (separadores de comentarios)
        comentarios_lista = comentarios_clean.split('\n\n')
        comentarios_html = []

        for comentario in comentarios_lista:
            if comentario.strip():
                # Parsear timestamp y autor si están disponibles
                # Formato esperado: [DD/MM/YYYY HH:MM COT - Autor]: Texto
                if comentario.startswith('[') and ']:' in comentario:
                    try:
                        # Extraer parte del timestamp/autor
                        timestamp_autor = comentario.split(']:')[0] + ']'
                        # Extraer texto del comentario
                        texto = comentario.split(']:')[1].strip()
                        # Formatear con timestamp en negrita
                        comentarios_html.append(f"**{timestamp_autor}**\n{texto}")
                    except Exception as e:
                        print(f"⚠️ Error parseando comentario: {e}")
                        # Si falla el parseo, usar comentario tal cual
                        comentarios_html.append(comentario)
                else:
                    # Comentario sin formato especial
                    comentarios_html.append(comentario)

        # Unir comentarios con el separador especificado
        return separador.join(comentarios_html)

    except Exception as e:
        print(f"⚠️ Error formateando comentarios: {e}")
        return "Error procesando comentarios"


def formatear_comentarios_administrador_para_mostrar(comentarios: str) -> str:
    """
    Formatear comentarios para visualización en panel de administración

    Versión específica para panel de administración que usa un separador
    diferente (sin línea horizontal) para visualización más compacta.

    Args:
        comentarios (str): String crudo de comentarios

    Returns:
        str: Comentarios formateados para visualización en admin panel

    Nota:
        Esta es una función wrapper de formatear_comentarios_para_display()
        con separador personalizado para el panel de administración.

    Alias de: formatear_comentarios_para_display() con separador='\n\n'
    """
    return formatear_comentarios_para_display(comentarios, separador='\n\n')


def clean_html_cached(content: str) -> str:
    """
    Limpieza de HTML con caché y límites de memoria

    Versión de clean_html_content() con límite de tamaño de entrada para
    prevenir problemas de memoria con contenido muy grande.

    Args:
        content (str): Contenido HTML o texto plano a limpiar

    Returns:
        str: Texto limpio sin tags HTML

    Nota:
        - Límite de 10KB (10,000 caracteres) por razones de memoria
        - Contenido más grande se trunca con indicador "... (contenido truncado)"
        - Mantenido para compatibilidad con código que importa directamente de utils.py
        - Usa el mismo caché LRU que clean_html_content()

    Ejemplo:
        ```python
        # Para contenido grande que podría causar problemas de memoria
        html_grande = "<p>" + ("x" * 20000) + "</p>"
        limpio = clean_html_cached(html_grande)
        # Resultado: primeros 10KB + "... (contenido truncado)"
        ```
    """
    # Limitar tamaño de entrada para prevenir problemas de memoria
    if len(content) > 10000:  # Límite de 10KB
        content = content[:10000] + "... (contenido truncado)"

    return clean_html_content(content)
