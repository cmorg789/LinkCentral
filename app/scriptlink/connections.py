"""Database connection configuration from YAML file."""
import base64
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.scriptlink.sql import SQLHelper

# Config file location
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
CONNECTIONS_FILE = CONFIG_DIR / "connections.yaml"

# Cached connections config
_connections_cache: Optional[Dict[str, Dict[str, Any]]] = None

# Cached SQLHelper instances
_sql_helpers: Dict[str, SQLHelper] = {}

# Fixed salt for key derivation (not secret, just ensures consistent key derivation)
_KEY_SALT = b"linkcentral_connections_v1"


def _get_fernet() -> Fernet:
    """Get a Fernet instance using SECRET_KEY from environment.

    Derives a proper Fernet key from the SECRET_KEY using PBKDF2.

    Raises:
        ValueError: If SECRET_KEY is not set
    """
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        raise ValueError(
            "SECRET_KEY environment variable is required to decrypt passwords. "
            "Set it in your .env file."
        )

    # Derive a 32-byte key from SECRET_KEY using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_KEY_SALT,
        iterations=100_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
    return Fernet(key)


def encrypt_password(password: str) -> str:
    """Encrypt a password for storage in connections.yaml.

    Use this to generate encrypted values for the password_encrypted field.

    Args:
        password: The plain text password to encrypt

    Returns:
        Encrypted password string to put in connections.yaml

    Example:
        >>> from app.scriptlink.connections import encrypt_password
        >>> print(encrypt_password("my_secret_password"))
        gAAAAABl...
    """
    fernet = _get_fernet()
    return fernet.encrypt(password.encode()).decode()


def _decrypt_password(encrypted: str) -> str:
    """Decrypt an encrypted password from connections.yaml.

    Args:
        encrypted: The encrypted password string

    Returns:
        Decrypted plain text password

    Raises:
        ValueError: If decryption fails (wrong key or corrupted data)
    """
    try:
        fernet = _get_fernet()
        return fernet.decrypt(encrypted.encode()).decode()
    except InvalidToken:
        raise ValueError(
            "Failed to decrypt password. Check that SECRET_KEY matches "
            "the key used to encrypt the password."
        )


def load_connections(force_reload: bool = False) -> Dict[str, Dict[str, Any]]:
    """Load database connections from config/connections.yaml.

    Connection passwords can be specified in three ways (in order of preference):
    1. `password_encrypted` - Encrypted password (recommended)
    2. `password_env` - Environment variable containing the password
    3. `password` - Plain text password (not recommended)

    Args:
        force_reload: If True, reload from disk even if cached

    Returns:
        Dict mapping connection name to connection config

    Example config/connections.yaml:
        connections:
          MyDatabase:
            driver: mssql
            host: sql.example.com
            port: 1433
            database: myavatar
            username: scriptlink_user
            password_encrypted: gAAAAABl...  # Encrypted with SECRET_KEY
            ssl_mode: disabled

          AnotherDB:
            driver: postgresql
            host: localhost
            port: 5432
            database: local
            username: admin
            password_env: ANOTHER_DB_PASSWORD  # From environment variable
    """
    global _connections_cache

    if _connections_cache is not None and not force_reload:
        return _connections_cache

    if not CONNECTIONS_FILE.exists():
        _connections_cache = {}
        return _connections_cache

    with open(CONNECTIONS_FILE, "r") as f:
        data = yaml.safe_load(f) or {}

    connections = data.get("connections", {})

    # Resolve password references (encrypted takes precedence)
    for name, config in connections.items():
        if "password_encrypted" in config:
            # Decrypt the password
            config["password"] = _decrypt_password(config["password_encrypted"])
            del config["password_encrypted"]
            # Remove password_env if also present (encrypted takes precedence)
            config.pop("password_env", None)
        elif "password_env" in config:
            # Fall back to environment variable
            env_var = config["password_env"]
            config["password"] = os.getenv(env_var, "")
            del config["password_env"]

    _connections_cache = connections
    return connections


def get_connection_config(name: str) -> Dict[str, Any]:
    """Get a connection configuration by name.

    Args:
        name: The connection name as defined in connections.yaml

    Returns:
        Connection config dict with keys: driver, host, port, database, username, password, ssl_mode, etc.

    Raises:
        ValueError: If connection not found in config
    """
    connections = load_connections()

    if name not in connections:
        available = ", ".join(connections.keys()) if connections else "(none configured)"
        raise ValueError(
            f"Connection '{name}' not found in config/connections.yaml. "
            f"Available connections: {available}"
        )

    return connections[name]


def reload_connections() -> None:
    """Force reload of connections config from disk.

    Call this if you've modified connections.yaml and want to pick up changes
    without restarting the server.
    """
    global _sql_helpers
    _sql_helpers = {}
    load_connections(force_reload=True)


def get_connection(name: str) -> SQLHelper:
    """Get a database connection by name.

    Connections are configured in config/connections.yaml and cached for reuse.

    Args:
        name: The connection name as defined in connections.yaml

    Returns:
        SQLHelper instance for executing queries

    Raises:
        ValueError: If connection not found in config

    Example:
        from app.scriptlink import get_connection

        conn = get_connection("AVATAR_DB")
        results = conn.query("SELECT * FROM patients WHERE id = :id", id=123)
    """
    if name in _sql_helpers:
        return _sql_helpers[name]

    config = get_connection_config(name)
    helper = SQLHelper(config)
    _sql_helpers[name] = helper
    return helper
