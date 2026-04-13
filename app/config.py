"""Application configuration."""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    soap_path: str = "/ScriptLinkService.asmx"
    service_name: str = "LinkCentral"
    debug: bool = False  # Enables auto-reload
    script_timeout: int = 30  # Max seconds for script execution
    script_error_blocking: bool = False # Should script errors block form?

    # Logging
    log_request_body: bool = False  # Log full request/response bodies in request_log

    # Database
    database_url: str = "sqlite:///data/scriptlink.db"

    # Logging cleanup
    cleanup_interval_minutes: int = 0  # How often to check for old logs
    cleanup_retention_days: int = 30  # Delete logs older than this

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


_PROJECT_ROOT = Path(__file__).parent.parent

settings = Settings()

# Resolve relative SQLite paths against the project root so the DB location
# is stable regardless of the working directory when the process starts.
if settings.database_url.startswith("sqlite:///") and not Path(settings.database_url[len("sqlite:///"):]).is_absolute():
    relative_path = settings.database_url[len("sqlite:///"):]
    resolved = (_PROJECT_ROOT / relative_path).resolve()
    settings.database_url = f"sqlite:///{resolved.as_posix()}"

# Ensure data directory exists
data_dir = _PROJECT_ROOT / "data"
data_dir.mkdir(exist_ok=True)
