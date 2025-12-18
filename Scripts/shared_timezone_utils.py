"""
Utilidades Compartidas de Zona Horaria
=======================================

Módulo crítico que consolida todas las funciones de conversión de zona horaria
entre Colombia (COT - UTC-5) y UTC para almacenamiento consistente en SharePoint.

REGLA FUNDAMENTAL DE ZONAS HORARIAS:
- ALMACENAMIENTO: Siempre en UTC en SharePoint
- VISUALIZACIÓN: Siempre en hora de Colombia (COT) para el usuario
- CONVERSIÓN: Usar SOLO las funciones de este módulo

Flujo típico:
    1. Usuario ingresa fecha → Hora Colombia (COT)
    2. Convertir a UTC → convertir_a_utc_para_almacenamiento()
    3. Guardar en SharePoint → UTC
    4. Leer de SharePoint → UTC
    5. Convertir a COT → convertir_a_colombia()
    6. Mostrar al usuario → Hora Colombia (COT)

Zona horaria:
    Colombia (America/Bogota): UTC-5 todo el año (NO usa horario de verano)

Casos especiales manejados:
- Objetos pandas Timestamp
- Fechas timezone-naive (se asume UTC o COT según contexto)
- Fechas timezone-aware (se convierten correctamente)
- Transiciones DST (aunque Colombia no las usa, el código es robusto)
- Strings en formato ISO

Autor: Equipo IGAC
Fecha: 2024-2025
"""

from datetime import datetime
from typing import Optional
import pytz

# Zona horaria de Colombia (UTC-5, sin horario de verano)
# Colombia NO cambia de hora durante el año
ZONA_HORARIA_COLOMBIA = pytz.timezone('America/Bogota')


def obtener_fecha_actual_colombia() -> datetime:
    """
    Obtener fecha y hora actual en zona horaria de Colombia

    Returns:
        datetime: Datetime actual con timezone Colombia (America/Bogota - UTC-5)

    Ejemplo:
        ```python
        ahora = obtener_fecha_actual_colombia()
        # Retorna algo como: 2024-12-17 14:30:00-05:00
        print(ahora.strftime('%d/%m/%Y %H:%M COT'))
        # Output: "17/12/2024 14:30 COT"
        ```

    Nota:
        - Retorna datetime con timezone-aware (incluye información de zona horaria)
        - Usar esta función en lugar de datetime.now() para consistencia
        - Colombia está en UTC-5 todo el año (no usa horario de verano)

    Alias disponible: now_colombia()
    """
    return datetime.now(ZONA_HORARIA_COLOMBIA)


# Alias para compatibilidad con aplicación de usuario
now_colombia = obtener_fecha_actual_colombia


def convertir_a_colombia(fecha_hora) -> Optional[datetime]:
    """
    Convertir cualquier datetime a zona horaria de Colombia

    Función robusta que maneja múltiples tipos de entrada y siempre retorna
    datetime en hora de Colombia o None si la conversión falla.

    Args:
        fecha_hora: Datetime a convertir. Puede ser:
                   - datetime timezone-aware (cualquier zona)
                   - datetime timezone-naive (asume UTC)
                   - pandas Timestamp
                   - string en formato ISO (2024-12-17T19:30:00Z)
                   - None (retorna None)

    Returns:
        Optional[datetime]: Datetime en zona horaria Colombia, o None si hay error

    Ejemplo:
        ```python
        # Desde UTC
        utc_time = datetime(2024, 12, 17, 19, 30, tzinfo=pytz.utc)
        col_time = convertir_a_colombia(utc_time)
        # Resultado: 2024-12-17 14:30:00-05:00 (5 horas menos)

        # Desde string ISO
        iso_string = "2024-12-17T19:30:00Z"
        col_time = convertir_a_colombia(iso_string)
        # Resultado: 2024-12-17 14:30:00-05:00

        # Desde pandas Timestamp
        import pandas as pd
        ts = pd.Timestamp('2024-12-17 19:30:00', tz='UTC')
        col_time = convertir_a_colombia(ts)
        # Resultado: 2024-12-17 14:30:00-05:00
        ```

    Nota:
        - Si el datetime no tiene timezone, se asume UTC
        - Maneja automáticamente pandas Timestamp objects
        - Soporta formato ISO con 'Z' o '+00:00'
        - Retorna None si la conversión falla (en lugar de lanzar excepción)
        - Registra warnings en consola para debugging

    Alias disponible: to_colombia_time()
    """
    if fecha_hora is None:
        return None

    try:
        # Manejar objetos pandas Timestamp (convertir a datetime de Python)
        if hasattr(fecha_hora, 'to_pydatetime'):
            fecha_hora = fecha_hora.to_pydatetime()

        # Manejar inputs de tipo string
        if isinstance(fecha_hora, str):
            try:
                # Probar formato ISO primero (más común)
                if 'T' in fecha_hora:
                    # Reemplazar 'Z' con '+00:00' para compatibilidad
                    fecha_hora = datetime.fromisoformat(fecha_hora.replace('Z', '+00:00'))
                else:
                    fecha_hora = datetime.fromisoformat(fecha_hora)
            except ValueError as e:
                print(f"⚠️ Formato de fecha string inválido: {fecha_hora} - {e}")
                return None

        # Validar que tenemos un objeto datetime
        if not isinstance(fecha_hora, datetime):
            print(f"⚠️ Tipo de fecha inválido: {type(fecha_hora)}")
            return None

        # Si el datetime no tiene timezone, asumir UTC
        if fecha_hora.tzinfo is None:
            try:
                fecha_hora = pytz.utc.localize(fecha_hora)
            except ValueError as e:
                print(f"⚠️ No se puede localizar datetime a UTC: {fecha_hora} - {e}")
                return None

        # Convertir a zona horaria de Colombia
        try:
            return fecha_hora.astimezone(ZONA_HORARIA_COLOMBIA)
        except (ValueError, AttributeError, OSError) as e:
            print(f"⚠️ No se puede convertir a zona horaria Colombia: {fecha_hora} - {e}")
            return None

    except Exception as e:
        print(f"❌ Error inesperado en conversión de zona horaria: {fecha_hora} - {e}")
        return None


# Alias para compatibilidad con aplicación de usuario
to_colombia_time = convertir_a_colombia


def convertir_a_utc_para_almacenamiento(fecha_hora) -> Optional[datetime]:
    """
    Convertir datetime de zona horaria Colombia a UTC para almacenamiento en SharePoint

    CRÍTICO: SharePoint almacena fechas en UTC. Esta función DEBE usarse antes
    de guardar cualquier datetime en SharePoint.

    Args:
        fecha_hora: Datetime a convertir. Puede ser:
                   - datetime timezone-aware (cualquier zona)
                   - datetime timezone-naive (asume hora Colombia)
                   - pandas Timestamp
                   - None (retorna None)

    Returns:
        Optional[datetime]: Datetime en UTC para almacenar, o None si hay error

    Ejemplo:
        ```python
        # Usuario ingresa fecha en hora Colombia
        colombia_time = obtener_fecha_actual_colombia()
        # Resultado: 2024-12-17 14:30:00-05:00

        # Convertir a UTC para SharePoint
        utc_time = convertir_a_utc_para_almacenamiento(colombia_time)
        # Resultado: 2024-12-17 19:30:00+00:00 (5 horas más)

        # Guardar en SharePoint
        sharepoint_data = {
            'FechaSolicitud': utc_time.isoformat() + 'Z'
        }
        ```

    Nota:
        - Si el datetime no tiene timezone, se asume hora de Colombia
        - Maneja transiciones DST (aunque Colombia no las usa)
        - Valida fechas sospechosas (más de 50 años de diferencia con hoy)
        - Retorna None si la conversión falla
        - Maneja automáticamente pandas Timestamp objects

    Casos especiales DST (aunque Colombia no los tiene):
        - AmbiguousTimeError: Usa hora estándar (is_dst=False)
        - NonExistentTimeError: Usa hora DST (is_dst=True)

    Alias disponible: to_utc_for_sharepoint()
    """
    if fecha_hora is None:
        return None

    try:
        # Manejar objetos pandas Timestamp
        if hasattr(fecha_hora, 'to_pydatetime'):
            fecha_hora = fecha_hora.to_pydatetime()

        # Validar que tenemos un objeto datetime
        if not isinstance(fecha_hora, datetime):
            print(f"⚠️ Tipo de fecha inválido para SharePoint: {type(fecha_hora)}")
            return None

        # Si el datetime no tiene timezone, asumir hora de Colombia
        if fecha_hora.tzinfo is None:
            try:
                fecha_hora = ZONA_HORARIA_COLOMBIA.localize(fecha_hora)
            except pytz.AmbiguousTimeError:
                # Manejar transiciones DST - usar hora estándar
                # (Colombia no usa DST, pero el código es robusto)
                fecha_hora = ZONA_HORARIA_COLOMBIA.localize(fecha_hora, is_dst=False)
                print(f"⚠️ Hora ambigua durante transición DST, usando hora estándar")
            except pytz.NonExistentTimeError:
                # Manejar horas no existentes - usar hora DST
                fecha_hora = ZONA_HORARIA_COLOMBIA.localize(fecha_hora, is_dst=True)
                print(f"⚠️ Hora no existente durante transición DST, usando hora DST")
            except ValueError as e:
                print(f"❌ No se puede localizar a zona horaria Colombia: {fecha_hora} - {e}")
                return None

        # Convertir a UTC
        try:
            utc_time = fecha_hora.astimezone(pytz.utc)

            # Validar que el resultado tiene sentido (no muy lejos en pasado/futuro)
            now = datetime.now(pytz.utc)
            if abs((utc_time - now).days) > 365 * 50:  # Chequeo de 50 años
                print(f"⚠️ Resultado de conversión de fecha sospechoso: {utc_time}")

            return utc_time

        except (ValueError, AttributeError, OSError) as e:
            print(f"❌ No se puede convertir a UTC: {fecha_hora} - {e}")
            return None

    except Exception as e:
        print(f"❌ Error inesperado en conversión a UTC para SharePoint: {fecha_hora} - {e}")
        return None


# Alias para compatibilidad con aplicación de usuario
to_utc_for_sharepoint = convertir_a_utc_para_almacenamiento


def formatear_fecha_colombia(fecha_hora, formato='%d/%m/%Y %H:%M COT') -> str:
    """
    Formatear datetime en zona horaria de Colombia como string

    Args:
        fecha_hora: Datetime a formatear (cualquier tipo soportado por convertir_a_colombia)
        formato (str): Formato strftime para la salida.
                      Por defecto: '%d/%m/%Y %H:%M COT' → "17/12/2024 14:30 COT"

    Returns:
        str: Fecha formateada en hora Colombia, o mensaje de error si falla

    Ejemplo:
        ```python
        # Formatear fecha UTC a hora Colombia
        utc_time = datetime(2024, 12, 17, 19, 30, tzinfo=pytz.utc)
        formatted = formatear_fecha_colombia(utc_time)
        # Resultado: "17/12/2024 14:30 COT"

        # Formato personalizado
        formatted = formatear_fecha_colombia(utc_time, '%d-%m-%Y %H:%M:%S')
        # Resultado: "17-12-2024 14:30:00"

        # Formato solo fecha
        formatted = formatear_fecha_colombia(utc_time, '%d/%m/%Y')
        # Resultado: "17/12/2024"
        ```

    Formatos comunes:
        - '%d/%m/%Y %H:%M COT' → "17/12/2024 14:30 COT" (por defecto)
        - '%d/%m/%Y' → "17/12/2024"
        - '%Y-%m-%d %H:%M:%S' → "2024-12-17 14:30:00"
        - '%A, %d de %B de %Y' → "martes, 17 de diciembre de 2024"

    Returns en caso de error:
        - "N/A" si fecha_hora es None
        - "Fecha no válida" si la conversión a Colombia falla
        - "Error de formato" si el formato strftime es inválido
        - "N/A" si hay error inesperado

    Nota:
        - Convierte automáticamente a hora Colombia antes de formatear
        - Maneja todos los tipos soportados por convertir_a_colombia()
        - Registra warnings en consola para debugging

    Alias disponible: format_colombia_datetime()
    """
    if fecha_hora is None:
        return "N/A"

    try:
        # Convertir a hora Colombia primero
        fecha_colombia = convertir_a_colombia(fecha_hora)
        if fecha_colombia:
            return fecha_colombia.strftime(formato)
        else:
            print(f"⚠️ No se pudo convertir fecha para formateo: {fecha_hora}")
            return "Fecha no válida"
    except (ValueError, TypeError) as e:
        print(f"⚠️ Error de formateo de fecha: {fecha_hora} - {e}")
        return "Error de formato"
    except Exception as e:
        print(f"❌ Error inesperado en formateo: {fecha_hora} - {e}")
        return "N/A"


# Alias para compatibilidad con aplicación de usuario
format_colombia_datetime = formatear_fecha_colombia
