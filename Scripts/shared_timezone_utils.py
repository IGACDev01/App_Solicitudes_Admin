"""
Shared timezone utilities for both Admin and User apps
Consolidates timezone conversion functions from both applications
"""
from datetime import datetime
from typing import Optional
import pytz

# Colombian timezone (UTC-5)
ZONA_HORARIA_COLOMBIA = pytz.timezone('America/Bogota')


def obtener_fecha_actual_colombia() -> datetime:
    """Get current date and time in Colombian timezone

    Aliases: now_colombia()
    """
    return datetime.now(ZONA_HORARIA_COLOMBIA)


# Alias for user app compatibility
now_colombia = obtener_fecha_actual_colombia


def convertir_a_colombia(fecha_hora) -> Optional[datetime]:
    """Convert any datetime to Colombian timezone

    Handles:
    - timezone-aware datetimes
    - timezone-naive datetimes (assumes UTC)
    - pandas Timestamp objects
    - string datetime formats

    Aliases: to_colombia_time()
    """
    if fecha_hora is None:
        return None

    try:
        # Handle pandas Timestamp objects
        if hasattr(fecha_hora, 'to_pydatetime'):
            fecha_hora = fecha_hora.to_pydatetime()

        # Handle string inputs
        if isinstance(fecha_hora, str):
            try:
                # Try ISO format first
                if 'T' in fecha_hora:
                    fecha_hora = datetime.fromisoformat(fecha_hora.replace('Z', '+00:00'))
                else:
                    fecha_hora = datetime.fromisoformat(fecha_hora)
            except ValueError as e:
                print(f"⚠️ Invalid date string format: {fecha_hora} - {e}")
                return None

        # Validate we have a datetime object
        if not isinstance(fecha_hora, datetime):
            print(f"⚠️ Invalid date type: {type(fecha_hora)}")
            return None

        # If datetime has no timezone, assume UTC
        if fecha_hora.tzinfo is None:
            try:
                fecha_hora = pytz.utc.localize(fecha_hora)
            except ValueError as e:
                print(f"⚠️ Cannot localize datetime to UTC: {fecha_hora} - {e}")
                return None

        # Convert to Colombian timezone
        try:
            return fecha_hora.astimezone(ZONA_HORARIA_COLOMBIA)
        except (ValueError, AttributeError, OSError) as e:
            print(f"⚠️ Cannot convert to Colombia timezone: {fecha_hora} - {e}")
            return None

    except Exception as e:
        print(f"❌ Unexpected timezone conversion error: {fecha_hora} - {e}")
        return None


# Alias for user app compatibility
to_colombia_time = convertir_a_colombia


def convertir_a_utc_para_almacenamiento(fecha_hora) -> Optional[datetime]:
    """Convert Colombian timezone to UTC for SharePoint storage

    Handles:
    - timezone-aware datetimes
    - timezone-naive datetimes (assumes Colombia time)
    - pandas Timestamp objects
    - DST transitions

    Aliases: to_utc_for_sharepoint()
    """
    if fecha_hora is None:
        return None

    try:
        # Handle pandas Timestamp objects
        if hasattr(fecha_hora, 'to_pydatetime'):
            fecha_hora = fecha_hora.to_pydatetime()

        # Validate we have a datetime object
        if not isinstance(fecha_hora, datetime):
            print(f"⚠️ Invalid date type for SharePoint: {type(fecha_hora)}")
            return None

        # If datetime has no timezone, assume Colombian time
        if fecha_hora.tzinfo is None:
            try:
                fecha_hora = ZONA_HORARIA_COLOMBIA.localize(fecha_hora)
            except pytz.AmbiguousTimeError:
                # Handle DST transitions - use standard time
                fecha_hora = ZONA_HORARIA_COLOMBIA.localize(fecha_hora, is_dst=False)
                print(f"⚠️ Ambiguous time during DST transition, using standard time")
            except pytz.NonExistentTimeError:
                # Handle non-existent times - use DST time
                fecha_hora = ZONA_HORARIA_COLOMBIA.localize(fecha_hora, is_dst=True)
                print(f"⚠️ Non-existent time during DST transition, using DST time")
            except ValueError as e:
                print(f"❌ Cannot localize to Colombia timezone: {fecha_hora} - {e}")
                return None

        # Convert to UTC
        try:
            utc_time = fecha_hora.astimezone(pytz.utc)

            # Validate result makes sense (not too far in past/future)
            now = datetime.now(pytz.utc)
            if abs((utc_time - now).days) > 365 * 50:  # 50 years check
                print(f"⚠️ Suspicious date conversion result: {utc_time}")

            return utc_time

        except (ValueError, AttributeError, OSError) as e:
            print(f"❌ Cannot convert to UTC: {fecha_hora} - {e}")
            return None

    except Exception as e:
        print(f"❌ Unexpected SharePoint timezone conversion error: {fecha_hora} - {e}")
        return None


# Alias for user app compatibility
to_utc_for_sharepoint = convertir_a_utc_para_almacenamiento


def formatear_fecha_colombia(fecha_hora, formato='%d/%m/%Y %H:%M COT') -> str:
    """Format datetime in Colombian timezone

    Args:
        fecha_hora: datetime object to format
        formato: strftime format string (default: '%d/%m/%Y %H:%M COT')

    Returns:
        Formatted date string or "N/A" if conversion fails

    Aliases: format_colombia_datetime()
    """
    if fecha_hora is None:
        return "N/A"

    try:
        fecha_colombia = convertir_a_colombia(fecha_hora)
        if fecha_colombia:
            return fecha_colombia.strftime(formato)
        else:
            print(f"⚠️ Could not convert date for formatting: {fecha_hora}")
            return "Fecha no válida"
    except (ValueError, TypeError) as e:
        print(f"⚠️ Date formatting error: {fecha_hora} - {e}")
        return "Error de formato"
    except Exception as e:
        print(f"❌ Unexpected formatting error: {fecha_hora} - {e}")
        return "N/A"


# Alias for user app compatibility
format_colombia_datetime = formatear_fecha_colombia
