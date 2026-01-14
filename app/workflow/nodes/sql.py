"""SQL Query node for database operations."""
import json
import logging
import ssl
from typing import Any, Optional, Tuple

from sqlalchemy import create_engine, text, URL

logger = logging.getLogger(__name__)

from app.workflow.nodes.base import BaseNode
from app.workflow.context import ExecutionContext
from app.database.models import Connection
from app.database.encryption import decrypt_password


def _build_connection_url(
    driver: str,
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    ssl_mode: str = "disabled",
    ssl_check_hostname: bool = True,
) -> Tuple[Any, dict]:
    """Build a SQLAlchemy URL and connect_args with SSL support.

    Args:
        ssl_mode: 'disabled', 'cert_none', 'cert_optional', 'cert_required'
        ssl_check_hostname: Whether to verify the server hostname matches the certificate

    Returns:
        Tuple of (URL, connect_args)
    """
    connect_args: dict = {}
    query: dict = {}

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
            # cert_optional or cert_required - verify certificate
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


class SQLQueryNode(BaseNode):
    """Executes a parameterized SQL query against a configured database connection.

    Properties:
        connection_id: ID of the configured database connection
        query: SQL query with :param placeholders
        parameters: Dict mapping parameter names to values/templates
        output_variable: Variable name to store query results

    Results are stored as a list of dictionaries, accessible via:
        @sql.output_variable.0.column - First row, specific column
        @sql.output_variable.*.column - All rows, specific column
        @var.output_variable - Entire result set as list
    """

    def execute(self, context: ExecutionContext) -> Optional[str]:
        """Execute the SQL query and store results."""
        connection_id = self.get_property("connection_id", "")
        query = self.get_property("query", "")
        parameters = self.get_property("parameters", {})
        output_variable = self.get_property("output_variable", "sql_result")

        if not connection_id or not query:
            return self.get_output("default")

        # Get db session from context
        if not context.db:
            context.variables[output_variable] = []
            return self.get_output("default")

        connection = context.db.query(Connection).filter(Connection.id == connection_id).first()
        if not connection:
            context.variables[output_variable] = []
            return self.get_output("default")

        # Parse connection data
        conn_data = json.loads(connection.connection_string_encrypted)
        password = decrypt_password(conn_data.get("password_encrypted", ""))

        # Resolve parameter templates
        resolved_params = {}
        for param_name, param_value in parameters.items():
            resolved_params[param_name] = context.resolve_template(str(param_value))

        logger.info("SQLQueryNode executing query: %s", query)
        logger.info("SQLQueryNode parameters: %s", resolved_params)

        engine = None
        try:
            # Build connection URL and connect_args
            conn_url, connect_args = _build_connection_url(
                driver=connection.driver,
                host=conn_data["host"],
                port=conn_data["port"],
                database=conn_data["database"],
                username=conn_data["username"],
                password=password,
                ssl_mode=conn_data.get("ssl_mode", "disabled"),
                ssl_check_hostname=conn_data.get("ssl_check_hostname", True),
            )

            # Execute query with connection pooling limits
            engine = create_engine(conn_url, connect_args=connect_args, pool_size=1, max_overflow=0)
            with engine.connect() as conn:
                result = conn.execute(text(query), resolved_params)

                # Convert to list of dicts with row limit to prevent DoS
                rows = []
                max_rows = 10000
                if result.returns_rows:
                    columns = result.keys()
                    for idx, row in enumerate(result):
                        if idx >= max_rows:
                            context.variables[f"{output_variable}_truncated"] = True
                            break
                        rows.append(dict(zip(columns, row)))

                context.variables[output_variable] = rows

        except Exception as e:
            # Store empty result and log error
            logger.exception("SQLQueryNode failed for query: %s", query)
            context.variables[output_variable] = []
            context.variables[f"{output_variable}_error"] = str(e)

        finally:
            # Always dispose the engine to prevent connection leaks
            if engine:
                engine.dispose()

        return self.get_output("default")
