"""Application configuration."""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8080
    soap_path: str = "/ScriptLinkService.asmx"

    # Database
    database_url: str = "sqlite:///data/scriptlink.db"

    # Security
    secret_key: str = "change-me-in-production"

    # Logging cleanup
    cleanup_interval_minutes: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure data directory exists
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)
