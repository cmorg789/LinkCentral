"""SQL Query node for database operations."""
import json
import ssl
from typing import Optional, Tuple

from sqlalchemy import create_engine, text

from app.workflow.nodes.base import BaseNode
from app.workflow.context import ExecutionContext
from app.database.models import Connection
from app.database.encryption import decrypt_password


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

        engine = None
        try:
            # Build connection string and connect_args
            conn_string, connect_args = _build_connection_string(
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
            engine = create_engine(conn_string, connect_args=connect_args, pool_size=1, max_overflow=0)
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
            # Store empty result and optionally log error
            context.variables[output_variable] = []
            context.variables[f"{output_variable}_error"] = str(e)

        finally:
            # Always dispose the engine to prevent connection leaks
            if engine:
                engine.dispose()

        return self.get_output("default")
