import pytz
from datetime import datetime
from typing import Optional
import pandas as pd

# Configure Colombia timezone - confirmed correct identifier
COLOMBIA_TZ = pytz.timezone('America/Bogota')

def get_colombia_time() -> datetime:
    """Get current time in Colombia timezone - FIXED"""
    # Always get UTC time first, then convert to Colombia
    utc_now = datetime.now(pytz.UTC)
    return utc_now.astimezone(COLOMBIA_TZ)

def get_colombia_time_string(format_str: str = '%d/%m/%Y %H:%M:%S') -> str:
    """Get current Colombia time as formatted string - FIXED"""
    colombia_time = get_colombia_time()
    return colombia_time.strftime(format_str)

def convert_to_colombia_time(dt) -> Optional[datetime]:
    """Convert any datetime to Colombia timezone - COMPLETELY FIXED"""
    if dt is None:
        return None
    
    try:
        # Handle pandas Timestamp objects
        if hasattr(dt, 'to_pydatetime'):
            dt = dt.to_pydatetime()
        
        # Handle string inputs
        if isinstance(dt, str):
            try:
                # Try parsing ISO format first
                if 'T' in dt:
                    dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                else:
                    dt = datetime.fromisoformat(dt)
            except ValueError:
                # Try pandas parsing as fallback
                dt = pd.to_datetime(dt).to_pydatetime()
        
        # Handle timezone-naive datetime objects
        if dt.tzinfo is None:
            # Assume naive datetimes are in UTC (SharePoint default)
            dt = pytz.UTC.localize(dt)
        
        # Convert to Colombia timezone
        colombia_dt = dt.astimezone(COLOMBIA_TZ)
        return colombia_dt
        
    except Exception as e:
        print(f"Error converting datetime to Colombia timezone: {e}")
        return None

def format_colombia_datetime(dt, format_str: str = '%d/%m/%Y %H:%M') -> str:
    """Format datetime in Colombia timezone - FIXED"""
    if dt is None:
        return "No disponible"
    
    try:
        colombia_dt = convert_to_colombia_time(dt)
        if colombia_dt is None:
            return "Error en fecha"
        return colombia_dt.strftime(format_str)
    except Exception as e:
        print(f"Error formatting datetime: {e}")
        return "Error en fecha"

def localize_colombia_time(naive_dt: datetime) -> datetime:
    """Properly localize a naive datetime to Colombia timezone using pytz.localize()"""
    if naive_dt is None:
        return None
    
    try:
        # Remove any existing timezone info first
        if naive_dt.tzinfo is not None:
            naive_dt = naive_dt.replace(tzinfo=None)
        
        # Use pytz.localize() method for proper timezone handling
        return COLOMBIA_TZ.localize(naive_dt)
    except Exception as e:
        print(f"Error localizing datetime to Colombia: {e}")
        return None

def normalize_datetime_for_comparison(dt) -> Optional[datetime]:
    """Normalize datetime to timezone-naive Colombia time for comparisons"""
    if dt is None:
        return None
    
    try:
        colombia_dt = convert_to_colombia_time(dt)
        if colombia_dt is None:
            return None
        
        # Return timezone-naive datetime in Colombia time for comparisons
        return colombia_dt.replace(tzinfo=None)
    except Exception as e:
        print(f"Error normalizing datetime: {e}")
        return None

def get_colombia_isoformat() -> str:
    """Get current Colombia time in ISO format for SharePoint"""
    colombia_time = get_colombia_time()
    # Convert to UTC for SharePoint storage
    utc_time = colombia_time.astimezone(pytz.UTC)
    return utc_time.isoformat().replace('+00:00', 'Z')

# Test function to verify timezone is working correctly
def test_timezone_functions():
    """Test function to verify timezone handling"""
    print("Testing timezone functions...")
    
    # Test current time
    current_colombia = get_colombia_time()
    print(f"Current Colombia time: {current_colombia}")
    print(f"Timezone: {current_colombia.tzinfo}")
    print(f"UTC offset: {current_colombia.strftime('%z')}")
    
    # Test string formatting
    formatted = get_colombia_time_string()
    print(f"Formatted Colombia time: {formatted}")
    
    # Test conversion from UTC
    utc_time = datetime.now(pytz.UTC)
    converted = convert_to_colombia_time(utc_time)
    print(f"UTC time: {utc_time}")
    print(f"Converted to Colombia: {converted}")
    
    # Test naive datetime localization
    naive_dt = datetime(2025, 7, 14, 12, 0, 0)
    localized = localize_colombia_time(naive_dt)
    print(f"Naive datetime: {naive_dt}")
    print(f"Localized to Colombia: {localized}")
    
    print("All tests completed!")

if __name__ == "__main__":
    test_timezone_functions()