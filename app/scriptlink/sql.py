"""SQL helper for database operations in scripts."""
import logging
import ssl
from typing import Any, Dict, List, Tuple

from sqlalchemy import create_engine, text, URL

logger = logging.getLogger(__name__)


def _build_connection_url(
    driver: str,
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    ssl_mode: str = "disabled",
    ssl_check_hostname: bool = True,
) -> Tuple[URL, dict]:
    """Build a SQLAlchemy URL and connect_args with SSL support.

    Args:
        ssl_mode: 'disabled', 'cert_none', 'cert_optional', 'cert_required'
        ssl_check_hostname: Whether to verify the server hostname matches the certificate

    Returns:
        Tuple of (URL, connect_args)
    """
    connect_args: dict = {}
    query: Dict[str, str] = {}

    if driver == "iris":
        drivername = "iris"

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

    elif driver == "mssql":
        drivername = "mssql+pyodbc"
        query["driver"] = "ODBC Driver 17 for SQL Server"

        if ssl_mode == "disabled":
            query["Encrypt"] = "no"
        elif ssl_mode == "cert_none":
            query["Encrypt"] = "yes"
            query["TrustServerCertificate"] = "yes"
        else:
            query["Encrypt"] = "yes"
            query["TrustServerCertificate"] = "no"

    elif driver == "postgresql":
        drivername = "postgresql"

        if ssl_mode == "disabled":
            query["sslmode"] = "disable"
        elif ssl_mode == "cert_none":
            query["sslmode"] = "require"
        elif ssl_mode == "cert_optional":
            query["sslmode"] = "prefer"
        else:  # cert_required
            query["sslmode"] = "verify-full" if ssl_check_hostname else "verify-ca"

    elif driver == "mysql":
        drivername = "mysql+pymysql"

        if ssl_mode == "disabled":
            query["ssl_disabled"] = "true"

    else:
        raise ValueError(f"Unsupported driver: {driver}")

    url = URL.create(
        drivername=drivername,
        username=username,
        password=password,
        host=host,
        port=port,
        database=database,
        query=query,
    )

    return url, connect_args


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
        self._name = f"{config.get('driver')}://{config.get('host')}:{config.get('port')}/{config.get('database')}"
        self._engine = self._create_engine()

    def _create_engine(self):
        """Create a SQLAlchemy engine for this connection."""
        url, connect_args = _build_connection_url(
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
            url,
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
        logger.debug("[%s] Query: %s | Params: %s", self._name, sql, params)
        with self._engine.connect() as conn:
            result = conn.execute(text(sql), params)

            rows = []
            if result.returns_rows:
                columns = result.keys()
                for idx, row in enumerate(result):
                    if idx >= max_rows:
                        break
                    rows.append(dict(zip(columns, row)))

            logger.debug("[%s] Query returned %d row(s)", self._name, len(rows))
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
        logger.debug("[%s] Scalar: %s | Params: %s", self._name, sql, params)
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
        logger.debug("[%s] Execute: %s | Params: %s", self._name, sql, params)
        with self._engine.connect() as conn:
            result = conn.execute(text(sql), params)
            conn.commit()
            logger.debug("[%s] Execute affected %d row(s)", self._name, result.rowcount)
            return result.rowcount
