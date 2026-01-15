"""SQL helper for database operations in scripts."""
import ssl
from typing import Any, Dict, List, Tuple

from sqlalchemy import create_engine, text


def _build_connection_string(
    driver: str,
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    ssl_mode: str = "disabled",
    ssl_check_hostname: bool = True,
) -> Tuple[str, dict]:
    """Build a SQLAlchemy connection string and connect_args with SSL support.

    Args:
        ssl_mode: 'disabled', 'cert_none', 'cert_optional', 'cert_required'
        ssl_check_hostname: Whether to verify the server hostname matches the certificate

    Returns:
        Tuple of (connection_string, connect_args)
    """
    connect_args: dict = {}

    if driver == "iris":
        conn_str = f"iris://{username}:{password}@{host}:{port}/{database}"

        if ssl_mode != "disabled":
            ssl_context = ssl.create_default_context()

            if ssl_mode == "cert_none":
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            elif ssl_mode == "cert_optional":
                ssl_context.verify_mode = ssl.CERT_OPTIONAL
                ssl_context.check_hostname = ssl_check_hostname
            else:  # cert_required
                ssl_context.verify_mode = ssl.CERT_REQUIRED
                ssl_context.check_hostname = ssl_check_hostname

            connect_args["sslcontext"] = ssl_context

        return conn_str, connect_args

    elif driver == "mssql":
        # MSSQL uses Encrypt and TrustServerCertificate params
        base = f"mssql+pyodbc://{username}:{password}@{host}:{port}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
        if ssl_mode == "disabled":
            base += "&Encrypt=no"
        elif ssl_mode == "cert_none":
            base += "&Encrypt=yes&TrustServerCertificate=yes"
        else:
            # cert_optional or cert_required - verify certificate
            base += "&Encrypt=yes&TrustServerCertificate=no"
        return base, connect_args

    elif driver == "postgresql":
        # PostgreSQL uses sslmode param
        base = f"postgresql://{username}:{password}@{host}:{port}/{database}"
        if ssl_mode == "disabled":
            return f"{base}?sslmode=disable", connect_args
        elif ssl_mode == "cert_none":
            return f"{base}?sslmode=require", connect_args
        elif ssl_mode == "cert_optional":
            return f"{base}?sslmode=prefer", connect_args
        else:  # cert_required
            if ssl_check_hostname:
                return f"{base}?sslmode=verify-full", connect_args
            else:
                return f"{base}?sslmode=verify-ca", connect_args

    elif driver == "mysql":
        # MySQL uses ssl_disabled or ssl params
        base = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
        if ssl_mode == "disabled":
            return f"{base}?ssl_disabled=true", connect_args
        else:
            # For MySQL, ssl is enabled by default when not disabled
            return base, connect_args

    else:
        raise ValueError(f"Unsupported driver: {driver}")


class SQLHelper:
    """Execute SQL queries against a configured database connection.

    Example:
        from app.scriptlink import get_connection

        conn = get_connection("AVATAR_DB")
        results = conn.query(
            "SELECT * FROM patients WHERE facility = :facility",
            facility=option_object.facility
        )

        for row in results:
            print(row["name"])

        count = conn.scalar("SELECT COUNT(*) FROM patients")
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize with a connection config dictionary.

        Args:
            config: Connection config with keys: driver, host, port, database, username, password
                    Optional: ssl_mode, ssl_check_hostname
        """
        self._config = config
        self._engine = self._create_engine()

    def _create_engine(self):
        """Create a SQLAlchemy engine for this connection."""
        conn_string, connect_args = _build_connection_string(
            driver=self._config["driver"],
            host=self._config["host"],
            port=self._config["port"],
            database=self._config["database"],
            username=self._config["username"],
            password=self._config.get("password", ""),
            ssl_mode=self._config.get("ssl_mode", "disabled"),
            ssl_check_hostname=self._config.get("ssl_check_hostname", True),
        )
        return create_engine(
            conn_string,
            connect_args=connect_args,
            pool_pre_ping=True,  # Verify connections before use
            pool_size=5,
            max_overflow=10,
        )

    def query(self, sql: str, max_rows: int = 10000, **params) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results as list of dicts.

        Args:
            sql: SQL query with :param placeholders
            max_rows: Maximum rows to return (default 10000)
            **params: Named parameters for the query

        Returns:
            List of dictionaries, one per row

        Example:
            results = conn.query(
                "SELECT * FROM patients WHERE id = :id",
                id="12345"
            )
        """
        with self._engine.connect() as conn:
            result = conn.execute(text(sql), params)

            rows = []
            if result.returns_rows:
                columns = result.keys()
                for idx, row in enumerate(result):
                    if idx >= max_rows:
                        break
                    rows.append(dict(zip(columns, row)))

            return rows

    def scalar(self, sql: str, **params) -> Any:
        """Execute a query and return the first column of the first row.

        Args:
            sql: SQL query with :param placeholders
            **params: Named parameters for the query

        Returns:
            Single value or None

        Example:
            count = conn.scalar("SELECT COUNT(*) FROM patients")
        """
        with self._engine.connect() as conn:
            result = conn.execute(text(sql), params)
            row = result.fetchone()
            return row[0] if row else None

    def execute(self, sql: str, **params) -> int:
        """Execute an INSERT/UPDATE/DELETE and return the row count.

        Args:
            sql: SQL statement with :param placeholders
            **params: Named parameters for the statement

        Returns:
            Number of affected rows

        Example:
            count = conn.execute(
                "UPDATE patients SET status = :status WHERE id = :id",
                status="active",
                id="12345"
            )
        """
        with self._engine.connect() as conn:
            result = conn.execute(text(sql), params)
            conn.commit()
            return result.rowcount
