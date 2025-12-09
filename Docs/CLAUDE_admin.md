# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Streamlit-based request management system** (Sistema de Gestión de Solicitudes) for IGAC. It's an administrative dashboard that manages requests through various departmental workflows using SharePoint as the backend data store.

**Key features:**
- Request lifecycle management across 13 departmental processes
- SharePoint integration via Microsoft Graph API
- Email notifications for state transitions
- Role-based access control by department
- Request filtering, searching, and analytics
- Excel export functionality
- Timezone handling for Colombia region
- Automatic app "wake-up" to prevent Streamlit cold starts

## Architecture

### High-Level Structure

```
App_Solicitudes_Admin/
├── Scripts/                    # Main application code
│   ├── main_admin.py          # Streamlit entry point - main dashboard
│   ├── admin_solicitudes.py   # Request management & state transitions
│   ├── dashboard.py           # Analytics & reporting views
│   ├── sharepoint_list_manager.py  # SharePoint/Graph API integration
│   ├── email_manager.py       # Email notifications
│   ├── state_flow_manager.py  # Request workflow state machine
│   ├── shared_*.py            # Utility modules (cache, filters, HTML, timezone)
│   └── utils.py               # General utilities
├── Scraper/                   # Web scraping scheduler (separate system)
├── Data/                      # Data files
├── Theme/                     # Streamlit custom theme files
├── Docs/                      # Documentation
└── requirements.txt           # Python dependencies
```

### Core Application Flow

1. **Entry Point**: `main_admin.py`
   - Initializes Streamlit page config (wide layout, minimal toolbar)
   - Sets up custom CSS branding (IGAC colors: #006AB3 primary, #38a962 footer)
   - Creates `GestorListasSharePoint` instance to connect to SharePoint
   - Caches SharePoint data with 5-minute TTL

2. **Data Source**: `sharepoint_list_manager.py`
   - Manages all SharePoint/Microsoft Graph API interactions
   - Handles OAuth2 authentication using tenant_id, client_id, client_secret from secrets
   - Uses retry logic for API calls (max 3 attempts with exponential backoff)
   - Caches access tokens with expiration tracking
   - Core list: "Data App Solicitudes" (request records)

3. **Business Logic Layers**:
   - **Admin Module** (`admin_solicitudes.py`): Request display, filtering, state transitions, inline editing
   - **State Management** (`state_flow_manager.py`): Validates allowed state transitions, tracks history
   - **Email Notifications** (`email_manager.py`): Sends notifications on state changes
   - **Dashboard** (`dashboard.py`): Analytics, charts, statistics

4. **Utilities**:
   - `shared_cache_utils.py`: Cache invalidation and key management
   - `shared_filter_utils.py`: DataFrame filtering logic
   - `shared_html_utils.py`: HTML content sanitization and formatting
   - `shared_timezone_utils.py`: Colombia timezone conversions
   - `utils.py`: Time calculations for request states

### Data Model

Request record structure (from SharePoint):
- `id_solicitud`: Unique request ID
- `nombre_solicitante`: Requester name
- `email_solicitante`: Requester email
- `fecha_solicitud`: Request creation date
- `tipo_solicitud`: Request type
- `estado`: Current state (workflow state)
- `proceso`: Department/process (e.g., "Almacén", "Contabilidad")
- `area`: Administrative area
- Plus many other fields for comments, attachments, dates, etc.

### Request Workflow States

The system manages request transitions through departmental workflows. State validation and transitions are handled by `StateFlowValidator` in `state_flow_manager.py`.

### Configuration

**Streamlit Config** (`.streamlit/config.toml`):
- Theme: Light with IGAC blue primary color (#006AB3)
- File watcher disabled (`fileWatcherType = "none"`)
- CORS and XSRF disabled for SharePoint integration
- FastReruns disabled to prevent module loading issues

**Secrets** (`.streamlit/secrets.toml` - NOT in git):
- `TENANT_ID`, `CLIENT_ID`, `CLIENT_SECRET`: Azure AD credentials for Graph API
- `SHAREPOINT_SITE_URL`: Target SharePoint site
- Admin credentials by department: `admin_almacen_usuario`, `admin_almacen_password`, etc.
- Email configuration (SMTP settings for notifications)

## Common Development Tasks

### Run the Application

```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Run main admin dashboard
streamlit run Scripts/main_admin.py

# Run with specific config
streamlit run Scripts/main_admin.py --logger.level=debug
```

### Install/Update Dependencies

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

### Run the App Wake-Up Scheduler

This prevents Streamlit from going into cold-start state:

```bash
# Windows - double-click or run:
RUN_WAKE_UP_SCHEDULER.bat

# Linux/Mac:
bash run_wake_up_scheduler.sh

# Direct Python:
.venv\Scripts\activate
python Scraper/app_wake_up_scheduler.py
```

See `Scraper/QUICK_START.md` for setup as Windows Task Scheduler job.

### Test Changes

Currently, no automated tests are set up. Testing is manual:
1. Run `streamlit run Scripts/main_admin.py`
2. Navigate to different request states
3. Verify SharePoint updates via Graph API
4. Check email notifications are sent
5. Validate cache invalidation behavior

### Debug SharePoint Connection

```python
# In Scripts/main_admin.py or test script:
from sharepoint_list_manager import GestorListasSharePoint
gestor = GestorListasSharePoint(nombre_lista="Data App Solicitudes")
df = gestor.df
print(df.head())
```

Common issues:
- Missing/expired secrets: Check `.streamlit/secrets.toml` exists and has all required keys
- Token errors: Verify Azure AD app registration has Graph API permissions
- Throttling: The code has retry logic; check Graph API quotas

### Cache Behavior

Streamlit caches are aggressive to improve performance:
- `obtener_datos_sharepoint_en_cache()`: 5-minute TTL for SharePoint data
- Cache invalidation: Call `invalidar_cache_datos()` after write operations
- Cache key: Can be forced to update with `forzar_actualizacion_cache()`

When modifying data, **always invalidate cache** or changes won't reflect:

```python
# Make changes to SharePoint...
invalidar_cache_datos()  # Force refresh on next load
```

### Key Dependencies

- **streamlit** (1.32.0): Web framework
- **pandas**: Data manipulation
- **plotly** (5.15.0): Charts and visualizations
- **requests**: HTTP calls (for Graph API)
- **openpyxl, xlsxwriter**: Excel export
- **pytz**: Timezone handling

## Important Patterns & Conventions

### Authentication & Secrets

All sensitive config is in `st.secrets` (loaded from `.streamlit/secrets.toml`):
- Never hardcode credentials
- Never commit secrets.toml
- SharePoint uses OAuth2 client credentials flow
- Admin login uses email/password from secrets (departmental)

### Error Handling

The code uses Streamlit's error display:
- `st.error()`: User-facing errors (shown in red)
- `print()`: Debug logging (goes to console/logs)
- Connection errors are logged but app may continue with cached data

### Timezone Handling

Colombia timezone is used throughout:
- `obtener_fecha_actual_colombia()`: Get current date in Colombia time
- `convertir_a_colombia()`: UTC → Colombia time
- `convertir_a_utc_para_almacenamiento()`: Colombia → UTC (for SharePoint storage)
- **Always use these functions** - don't use Python's default UTC

### HTML Content Sanitization

User-provided HTML (comments, descriptions) is sanitized:
- `limpiar_contenido_html()`: Removes dangerous tags/scripts
- `formatear_comentarios_administrador_para_mostrar()`: Safe HTML rendering in Streamlit

## Troubleshooting

### App Won't Start

1. Check `.streamlit/secrets.toml` exists in project root
2. Verify Python 3.8+ in virtual environment
3. Check all dependencies installed: `pip install -r requirements.txt`
4. Look for import errors: `python -c "from Scripts.sharepoint_list_manager import GestorListasSharePoint"`

### Slow Performance

- SharePoint queries are cached for 5 minutes
- Large datasets (1000+ records) trigger memory optimization
- If queries are still slow, check Graph API throttling

### SharePoint Connection Fails

- Verify credentials in secrets are correct
- Check Azure AD app has "Directory.Read.All" and "Sites.ReadWrite.All" permissions
- Verify `SHAREPOINT_SITE_URL` matches actual SharePoint site
- Token retry logic handles temporary failures; watch logs for persistent errors

### Cache Not Updating

After changes, call:
```python
st.cache_data.clear()  # or use invalidar_cache_datos()
```

Or force a cache key refresh for specific cached function.

## Related Documentation

- `Scraper/QUICK_START.md`: App wake-up scheduler setup
- `Scraper/SCHEDULER_SUMMARY.md`: Scheduler implementation details
- `Scraper/WHAT_WAS_DONE.md`: Historical context on scraper setup
