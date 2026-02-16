# LinkCentral

SOAP middleware for Netsmart myAvatar's ScriptLink API. Routes form event requests to Python scripts based on parameter name.

## How It Works

1. A myAvatar form event sends a SOAP POST to `/ScriptLinkService.asmx`
2. `RunScript` receives an `OptionObject` and a parameter name (e.g. `"ADMIT"`)
3. The parameter is matched to a script file (`scripts/ADMIT.py`)
4. The script runs with an `OptionObjectWrapper` that tracks field changes
5. A response is built from the diff (only modified fields) and returned to myAvatar

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure as needed:

```bash
cp .env.example .env
# Edit .env -- see Environment Variables below for options
```

If using `password_encrypted` in `connections.yaml`, set `SECRET_KEY` (minimum 32 characters):
```bash
# Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Run the Server

```bash
# Development (with auto-reload)
python -m app.main --reload

# Production
python -m app.main
```

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `{SOAP_PATH}` | SOAP service |
| `{SOAP_PATH}?wsdl` | WSDL definition |
| `/health` | Health check |

`SOAP_PATH` defaults to `/ScriptLinkService.asmx` and can be changed in `.env`.

## Writing Scripts

Create a Python file in `scripts/` matching the ScriptLink parameter name. Scripts are discovered automatically at runtime -- no restart needed.

See `scripts/_example.py` for a thorough template with most (all?) available features.

## Testing Scripts Locally

You can test scripts locally without going through myAvatar using captured JSON fixtures:

```bash
# Run a script against a fixture file
python -m app.scriptlink test ADMIT data/missing_scripts/ADMIT_2026-01-16_143522.json

# With verbose output (shows print() statements from the script)
python -m app.scriptlink test ADMIT fixture.json --verbose

# Quote arguments that contain spaces
python -m app.scriptlink test "MY PARAM" "data/missing scripts/fixture.json"
```

### Development Workflow

1. **Trigger the request** from myAvatar (the script doesn't need to exist yet)
2. **Fixture is saved** automatically to `data/missing_scripts/{PARAM}_{timestamp}.json`
3. **Create the script** at `scripts/{PARAM}.py`
4. **Test locally** with `python -m app.scriptlink test {PARAM} data/missing_scripts/{fixture}.json --verbose`
5. **Iterate** until the output is correct
6. **Deploy** to the server -- hot reload picks up changes immediately

## Script API Reference

### Field Access

```python
# Get value (safe, returns default if not found)
value = option_object.fields.get("123.45", "")

# Get value (raises KeyError if not found)
value = option_object.fields["123.45"].value

# Set value (tracked for diff)
option_object.fields["123.45"] = "New Value"

# Set field properties
option_object.fields["123.45"].required = True
option_object.fields["123.45"].enabled = False
option_object.fields["123.45"].locked = True
```

### Metadata (read-only)

| Property | Description |
|----------|-------------|
| `entity_id` | Patient/Entity ID |
| `facility` | Facility code |
| `episode_number` | Episode number |
| `option_user_id` | Current user ID |
| `option_staff_id` | Current staff ID |
| `option_id` | Option ID |
| `system_code` | System code |

```python
entity_id = option_object.entity_id
facility = option_object.facility
```

### Error Types

Raise these exceptions to control form behavior:

| Exception | Code | Behavior |
|-----------|------|----------|
| `ValidationError` | 1 | Block form submission with error |
| `OkCancelError` | 2 | OK/Cancel dialog |
| `AlertError` | 3 | Info popup, allows submission |
| `ConfirmError` | 4 | Yes/No dialog |
| `OpenUrlError` | 5 | Opens URL in browser |
| `OpenFormError` | 6 | Opens another form |

```python
from app.scriptlink import ValidationError, AlertError

raise ValidationError("Patient name is required")  # Blocks form
raise AlertError("Record updated successfully")     # Info only
```

You can also set responses directly on the wrapper:

```python
option_object.set_error("Something went wrong")
option_object.set_alert("Info message")
option_object.open_url("https://example.com")
option_object.open_form("FORM_ID")
```

### Database Access

Configure connections in `config/connections.yaml` (copy from `connections.example.yaml`):

```python
from app.scriptlink import get_connection

conn = get_connection("MyDatabase")

# SELECT - returns list of dicts
results = conn.query("SELECT * FROM patients WHERE id = :id", id=entity_id)

# Single value
count = conn.scalar("SELECT COUNT(*) FROM patients")

# INSERT/UPDATE/DELETE - returns row count
conn.execute("UPDATE patients SET name = :name WHERE id = :id", name="John", id=123)
```

Always use named parameters (`:param`) to prevent SQL injection.

## Database Connections

Configure in `config/connections.yaml`:

```yaml
connections:
  AVATAR_DB:
    driver: iris
    host: sql.example.com
    port: 1972
    database: AVPM
    username: LIVE:scriptlink_user
    password_encrypted: gAAAAABl...
    ssl_mode: disabled
```

**Supported drivers:** `mssql`, `postgresql`, `iris`, `mysql`

**Password options** (in order of preference):

1. `password_encrypted` -- Fernet encrypted (recommended)
2. `password_env` -- Environment variable name
3. `password` -- Plain text (not recommended)

**Encrypt a password:**

```bash
# If SECRET_KEY is in .env or environment
python -m app.scriptlink encrypt-password

# If SECRET_KEY is only in the service XML
python -m app.scriptlink encrypt-password --secret-key "your_secret_key"
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(none)* | 32+ char key for password encryption (required if using `password_encrypted`) |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `SOAP_PATH` | `/ScriptLinkService.asmx` | SOAP endpoint path |
| `DATABASE_URL` | `sqlite:///data/scriptlink.db` | Request log database |
| `SCRIPT_TIMEOUT` | `30` | Script timeout in seconds |
| `SCRIPT_ERROR_BLOCKING` | `False` | Unhandled errors block form |
| `CLEANUP_INTERVAL_MINUTES` | `0` | How often to prune old request logs (0 = disabled) |
| `CLEANUP_RETENTION_DAYS` | `30` | Delete logs older than this many days |
| `DEBUG` | `False` | Verbose logging |

## Deployment

See `docs/` for platform-specific deployment guides:

- [Windows](docs/windows/) -- WinSW service setup
- [Linux](docs/linux/) -- systemd service setup

## Directory Structure

```
app/                    # Python backend
  main.py               # FastAPI entry point, mounts SOAP service
  config.py             # Pydantic settings (env vars)
  db.py                 # SQLAlchemy models (RequestLog)
  soap/                 # SOAP service (ScriptLink)
    service.py          # RunScript endpoint, routes to scripts
    types.py            # OptionObject2015 WSDL types
  scriptlink/           # Script API library
    __init__.py         # Public exports
    option_object.py    # OptionObjectWrapper with diff tracking
    router.py           # Script discovery by parameter name
    sql.py              # SQLHelper for database queries
    connections.py      # YAML config loader + get_connection()
    errors.py           # ValidationError, AlertError, etc.
    test.py             # CLI testing utility
scripts/                # User scripts (one .py per parameter)
  _example.py           # Template script
docs/                   # Deployment guides
  windows/              # WinSW service configs + setup
  linux/                # systemd setup
config/                 # Configuration files
  connections.yaml      # Database connection configs
data/                   # Runtime data
  scriptlink.db         # SQLite database (request logs)
  missing_scripts/      # Captured fixtures for unknown parameters
```
