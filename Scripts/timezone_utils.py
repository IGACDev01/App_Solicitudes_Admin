import pytz
from datetime import datetime
from typing import Optional

# Colombian timezone
COLOMBIA_TZ = pytz.timezone('America/Bogota')

def now_colombia() -> datetime:
    """Get current time in Colombian timezone"""
    return datetime.now(COLOMBIA_TZ)

def to_colombia(dt) -> Optional[datetime]:
    """Convert any datetime to Colombian timezone"""
    if dt is None:
        return None
    
    try:
        # If datetime is timezone-naive, assume UTC
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        
        # Convert to Colombian time
        return dt.astimezone(COLOMBIA_TZ)
    except:
        return dt

def to_utc_for_storage(dt) -> Optional[datetime]:
    """Convert Colombian time to UTC for storage"""
    if dt is None:
        return None
    
    try:
        # If timezone-naive, assume Colombian time
        if dt.tzinfo is None:
            dt = COLOMBIA_TZ.localize(dt)
        
        # Convert to UTC
        return dt.astimezone(pytz.utc)
    except:
        return dt

def format_colombia_time(dt, format_str='%d/%m/%Y %H:%M COT') -> str:
    """Format datetime in Colombian timezone"""
    if dt is None:
        return "N/A"
    
    colombia_time = to_colombia(dt)
    if colombia_time:
        return colombia_time.strftime(format_str)
    return "N/A"