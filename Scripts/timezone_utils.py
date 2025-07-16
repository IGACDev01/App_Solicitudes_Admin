import pytz
from datetime import datetime
from typing import Optional

# Zona horaria de Colombia
ZONA_HORARIA_COLOMBIA = pytz.timezone('America/Bogota')

def obtener_fecha_actual_colombia() -> datetime:
    """Obtiene la fecha y hora actual en zona horaria de Colombia"""
    return datetime.now(ZONA_HORARIA_COLOMBIA)

def convertir_a_colombia(fecha_hora) -> Optional[datetime]:
    """Convierte cualquier datetime a zona horaria de Colombia"""
    if fecha_hora is None:
        return None
    
    try:
        # Si el datetime no tiene zona horaria, asumir UTC
        if fecha_hora.tzinfo is None:
            fecha_hora = pytz.utc.localize(fecha_hora)
        
        # Convertir a hora colombiana
        return fecha_hora.astimezone(ZONA_HORARIA_COLOMBIA)
    except:
        return fecha_hora

def convertir_a_utc_para_almacenamiento(fecha_hora) -> Optional[datetime]:
    """Convierte hora colombiana a UTC para almacenamiento en SharePoint"""
    if fecha_hora is None:
        return None
    
    try:
        # Si no tiene zona horaria, asumir hora colombiana
        if fecha_hora.tzinfo is None:
            fecha_hora = ZONA_HORARIA_COLOMBIA.localize(fecha_hora)
        
        # Convertir a UTC
        return fecha_hora.astimezone(pytz.utc)
    except:
        return fecha_hora

def formatear_fecha_colombia(fecha_hora, formato='%d/%m/%Y %H:%M COT') -> str:
    """Formatea datetime en zona horaria colombiana"""
    if fecha_hora is None:
        return "N/A"
    
    fecha_colombia = convertir_a_colombia(fecha_hora)
    if fecha_colombia:
        return fecha_colombia.strftime(formato)
    return "N/A"