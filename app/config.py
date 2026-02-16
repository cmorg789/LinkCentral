"""Application configuration."""
from typing import Optional
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8080
    soap_path: str = "/ScriptLinkService.asmx"
    debug: bool = False  # Enables auto-reload
    script_timeout: int = 30  # Max seconds for script execution
    script_error_blocking: bool = False # Should script errors block form?

    # Database
    database_url: str = "sqlite:///data/scriptlink.db"

    # Security - only required if using password_encrypted in connections.yaml
    secret_key: Optional[str] = None

    # Logging cleanup
    cleanup_interval_minutes: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure data directory exists
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)
