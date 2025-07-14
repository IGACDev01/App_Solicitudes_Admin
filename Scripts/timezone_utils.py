import pytz
from datetime import datetime
from typing import Optional

# Configure your local timezone
COLOMBIA_TZ = pytz.timezone('America/Bogota')

def get_colombia_time() -> datetime:
    """Get current time in Colombia timezone"""
    return datetime.now(COLOMBIA_TZ)

def get_colombia_time_string(format_str: str = '%d/%m/%Y %H:%M:%S') -> str:
    """Get current Colombia time as formatted string"""
    return get_colombia_time().strftime(format_str)

def convert_to_colombia_time(dt: datetime) -> datetime:
    """Convert any datetime to Colombia timezone"""
    if dt is None:
        return None
    
    try:
        # If datetime is naive (no timezone), assume it's UTC
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        
        # Convert to Colombia timezone
        return dt.astimezone(COLOMBIA_TZ)
    except Exception as e:
        print(f"Error converting timezone: {e}")
        return dt

def format_colombia_datetime(dt: datetime, format_str: str = '%d/%m/%Y %H:%M') -> str:
    """Format datetime in Colombia timezone"""
    if dt is None:
        return "No disponible"
    
    try:
        colombia_dt = convert_to_colombia_time(dt)
        return colombia_dt.strftime(format_str)
    except Exception as e:
        print(f"Error formatting datetime: {e}")
        return "Error en fecha"