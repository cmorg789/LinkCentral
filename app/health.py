"""Health check aggregation for the /health endpoint.

Runs a set of dependency checks and rolls them up into an overall status:

  * healthy   - everything passed (HTTP 200)
  * degraded  - the service is up and serving, but something is impaired:
                a configured external DB is unreachable, or the script
                admission queue is full (HTTP 200 - still in rotation)
  * unhealthy - core infrastructure is broken: the request-log DB, which
                every request writes to, cannot be reached (HTTP 503)

Pinging the external myAvatar databases happens concurrently with a per-
connection wall-clock timeout, so one hung DB cannot stall the probe.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from sqlalchemy import text

from app import __version__
from app.config import settings
from app.db import engine
from app.scriptlink.connections import get_connection, load_connections
from app.soap.service import get_script_pool_stats

logger = logging.getLogger(__name__)

# Status constants ordered by severity so the overall status is the worst.
HEALTHY = "healthy"
DEGRADED = "degraded"
UNHEALTHY = "unhealthy"

_SEVERITY = {HEALTHY: 0, DEGRADED: 1, UNHEALTHY: 2}


def _check_request_log_db() -> dict:
    """Ping the application's own request-log database (core dependency)."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": HEALTHY}
    except Exception as e:
        logger.warning("Health check: request-log DB unreachable: %s", e)
        return {"status": UNHEALTHY, "error": str(e)}


def _ping_connection(name: str) -> dict:
    """Ping a single configured connection within the per-connection timeout."""
    try:
        get_connection(name).ping()
        return {"status": HEALTHY}
    except Exception as e:
        logger.warning("Health check: connection %r unreachable: %s", name, e)
        return {"status": DEGRADED, "error": str(e)}


def _check_connections() -> dict:
    """Ping every configured connection concurrently, each with a timeout.

    External DB failures are reported as ``degraded`` rather than
    ``unhealthy``: the SOAP service itself is still up and scripts that don't
    use the failing database continue to work.
    """
    connections = load_connections()
    if not connections:
        return {}

    results: dict = {}
    timeout = settings.health_connection_timeout
    with ThreadPoolExecutor(max_workers=min(8, len(connections)),
                            thread_name_prefix="health-ping") as pool:
        futures = {pool.submit(_ping_connection, name): name for name in connections}
        for future, name in futures.items():
            try:
                results[name] = future.result(timeout=timeout)
            except FuturesTimeoutError:
                logger.warning("Health check: connection %r timed out after %ss", name, timeout)
                results[name] = {"status": DEGRADED, "error": f"ping timed out after {timeout}s"}
            except Exception as e:  # pragma: no cover - defensive
                results[name] = {"status": DEGRADED, "error": str(e)}
    return results


def _check_script_pool() -> dict:
    """Report script executor saturation; a full admission queue is degraded."""
    stats = get_script_pool_stats()
    status = DEGRADED if stats["queue_full"] else HEALTHY
    return {"status": status, **stats}


def run_health_checks() -> dict:
    """Run all checks and return a report with an overall rolled-up status."""
    checks: dict = {
        "request_log_db": _check_request_log_db(),
        "script_pool": _check_script_pool(),
    }

    if settings.health_check_connections:
        conn_results = _check_connections()
        if conn_results:
            checks["connections"] = conn_results

    # Overall status is the worst severity across every individual check.
    worst = HEALTHY
    for check in checks.values():
        statuses = (
            [c["status"] for c in check.values()]
            if "status" not in check  # nested (e.g. connections) dict-of-dicts
            else [check["status"]]
        )
        for status in statuses:
            if _SEVERITY[status] > _SEVERITY[worst]:
                worst = status

    return {"status": worst, "version": __version__, "checks": checks}
