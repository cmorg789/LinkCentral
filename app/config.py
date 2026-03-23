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

    # Database
    database_url: str = "sqlite:///data/scriptlink.db"

    # Logging cleanup
    cleanup_interval_minutes: int = 0  # How often to check for old logs
    cleanup_retention_days: int = 30  # Delete logs older than this

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure data directory exists
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)
