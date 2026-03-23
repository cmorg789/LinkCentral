"""Database connection configuration from YAML file."""
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from app.scriptlink.sql import SQLHelper

# Config file location
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
CONNECTIONS_FILE = CONFIG_DIR / "connections.yaml"

# Cached connections config
_connections_cache: Optional[Dict[str, Dict[str, Any]]] = None

# Cached SQLHelper instances
_sql_helpers: Dict[str, SQLHelper] = {}


def load_connections(force_reload: bool = False) -> Dict[str, Dict[str, Any]]:
    """Load database connections from config/connections.yaml.

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
            password: my_password
            ssl_mode: disabled
    """
    global _connections_cache

    if _connections_cache is not None and not force_reload:
        return _connections_cache

    if not CONNECTIONS_FILE.exists():
        _connections_cache = {}
        return _connections_cache

    with open(CONNECTIONS_FILE, "r") as f:
        data = yaml.safe_load(f) or {}

    _connections_cache = data.get("connections", {})
    return _connections_cache


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
    # Dispose old engines to release database connections
    for helper in _sql_helpers.values():
        helper._engine.dispose()
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
