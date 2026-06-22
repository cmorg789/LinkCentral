"""SOAP service implementation for ScriptLink."""
import io
import json
import logging
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from spyne import Application, Service, rpc
from spyne.decorator import srpc
from spyne.model.primitive import Unicode
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

from app import __version__
from app.config import settings
from app.db import get_session, RequestLog
from app.soap.types import OptionObject2015, ErrorCodes, TNS
from app.scriptlink import ScriptRouter, OptionObjectWrapper, ScriptLinkError, AlertError

logger = logging.getLogger(__name__)

# Thread-local stdout capture: allows each thread to capture print() output
# independently without clobbering other threads' sys.stdout.
_thread_local = threading.local()
_original_stdout = sys.stdout


class _ThreadLocalStdout:
    """A sys.stdout replacement that routes writes to a per-thread buffer when set."""

    def write(self, text):
        buf = getattr(_thread_local, "capture_buffer", None)
        if buf is not None:
            buf.write(text)
        else:
            _original_stdout.write(text)

    def flush(self):
        buf = getattr(_thread_local, "capture_buffer", None)
        if buf is not None:
            buf.flush()
        else:
            _original_stdout.flush()

    # Delegate attribute access (encoding, fileno, etc.) to the real stdout
    def __getattr__(self, name):
        return getattr(_original_stdout, name)


# Install once at module load
sys.stdout = _ThreadLocalStdout()

# Initialize the script router
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
DATA_DIR = Path(__file__).parent.parent.parent / "data"
_router = ScriptRouter(SCRIPTS_DIR, DATA_DIR)

# Shared executor for script execution.
# Concurrency model:
#   * `_script_executor` bounds *running* scripts to script_max_concurrency.
#   * `_script_admission` bounds *total in-flight* (running + queued) to
#     script_max_concurrency + script_max_queued. This matters because
#     ThreadPoolExecutor's internal queue is unbounded — without a gate,
#     saturated workers would still let new tasks pile up in memory and
#     potentially execute long after the caller timed out.
#   * On caller timeout we call future.cancel(): if the task hasn't started
#     yet it's dropped from the queue so stale work doesn't run later.
# NOTE: Python threads cannot be forcibly killed, so a running script that
# exceeds the timeout keeps executing in the background until it returns.
# True termination would require a process pool (heavier; needs pickleable
# OptionObject).
_script_executor = ThreadPoolExecutor(
    max_workers=settings.script_max_concurrency,
    thread_name_prefix="scriptlink",
)
_script_admission = threading.BoundedSemaphore(
    settings.script_max_concurrency + settings.script_max_queued
)

# Log cleanup state
_last_cleanup_time: Optional[datetime] = None


def get_script_pool_stats() -> dict:
    """Snapshot of script executor saturation for health reporting.

    Derived from the admission semaphore, which gates total in-flight work
    (running + queued) at ``max_concurrency + max_queued``. Reading the
    semaphore's free-permit count is an atomic snapshot; it may be momentarily
    stale under concurrency but is accurate enough for a health probe.
    """
    capacity = settings.script_max_concurrency + settings.script_max_queued
    # BoundedSemaphore._value is the number of free admission slots.
    available = _script_admission._value
    in_flight = capacity - available
    running = min(in_flight, settings.script_max_concurrency)
    queued = max(0, in_flight - settings.script_max_concurrency)
    return {
        "running": running,
        "queued": queued,
        "max_concurrency": settings.script_max_concurrency,
        "max_queued": settings.script_max_queued,
        "queue_full": available == 0,
    }


class ScriptLinkService(Service):
    """SOAP service implementing the ScriptLink interface."""

    __service_name__ = "LinkCentral"

    @srpc(_returns=Unicode)
    def GetVersion():
        """Return the version string of the ScriptLink service.

        myAvatar uses this to verify connectivity.
        """
        return __version__

    @srpc(OptionObject2015, Unicode, _returns=OptionObject2015)
    def RunScript(optionObject, parameter):
        """Process form data and return modifications.

        Routes to a Python script based on the parameter name.
        Scripts are located in the /scripts directory with filename matching the parameter.

        Args:
            optionObject: The OptionObject2015 containing form state
            parameter: String used to route to the appropriate script (e.g., "ADMIT" -> scripts/ADMIT.py)

        Returns:
            Modified OptionObject2015
        """
        start_time = time.time()
        source_ip = getattr(_thread_local, "source_ip", None)

        with get_session() as db:
            # Create wrapper for Pythonic access
            wrapper = OptionObjectWrapper(optionObject)
            input_json = json.dumps(wrapper.to_dict()) if settings.log_request_body else None

            try:
                # Find script handler
                handler = _router.get_handler(parameter)

                if handler is None:
                    # No script found - save request data for development and return error
                    execution_time_ms = int((time.time() - start_time) * 1000)

                    # Save the request data to help develop the script
                    _router.save_missing_script_data(parameter, wrapper.to_dict())

                    # Log the unconfigured request
                    log_entry = RequestLog(
                        parameter=parameter,
                        option_object=input_json,
                        response_object=None,
                        status="no_script",
                        error_message=f"Script not configured: {parameter}",
                        execution_time_ms=execution_time_ms,
                        source_ip=source_ip,
                    )
                    db.add(log_entry)
                    db.commit()
                    _maybe_cleanup_logs()

                    # Return error response
                    optionObject.ErrorCode = ErrorCodes.ALERT
                    optionObject.ErrorMesg = f"Script not configured: {parameter}"
                    return _build_minimal_response(optionObject)

                # Script found - execute with stdout capture and timeout
                def run_script():
                    captured = io.StringIO()
                    _thread_local.capture_buffer = captured
                    try:
                        res = handler(wrapper)
                        return res, captured.getvalue()
                    finally:
                        _thread_local.capture_buffer = None

                # Gate admission so queue depth stays bounded even under load.
                if not _script_admission.acquire(blocking=False):
                    logger.warning(
                        "Script %r rejected: admission queue full (max_concurrency=%d, max_queued=%d)",
                        parameter, settings.script_max_concurrency, settings.script_max_queued,
                    )
                    raise AlertError(
                        "LinkCentral is temporarily overloaded. Please retry in a moment."
                    )

                future = _script_executor.submit(run_script)
                # Release the admission slot whenever the task finishes for any
                # reason — completed, errored, or cancelled while queued.
                future.add_done_callback(lambda _f: _script_admission.release())

                try:
                    result, script_output = future.result(timeout=settings.script_timeout)
                except FuturesTimeoutError:
                    # Try to drop the task if it hasn't started yet; if it has
                    # started, the thread keeps running until it returns.
                    cancelled = future.cancel()
                    logger.warning(
                        "Script %r timed out after %ss (%s)",
                        parameter,
                        settings.script_timeout,
                        "queued task dropped" if cancelled else "thread will continue until it returns",
                    )
                    raise TimeoutError(f"Script timed out after {settings.script_timeout}s")

                # Log any print output from the script
                if script_output:
                    logger.info(f"[{parameter}] {script_output.rstrip()}")

                # If script returned None, build response from wrapper
                if result is None:
                    result = wrapper.build_response()

                execution_time_ms = int((time.time() - start_time) * 1000)

                # Get diff for logging
                diff = wrapper.get_diff()

                # Log the request
                log_entry = RequestLog(
                    parameter=parameter,
                    option_object=input_json,
                    response_object=_option_object_to_json(result) if settings.log_request_body else None,
                    execution_context=json.dumps({"diff": diff, "output": script_output}) if (diff or script_output) else None,
                    status="success" if result.ErrorCode == ErrorCodes.NONE else "error",
                    error_message=result.ErrorMesg if result.ErrorCode != ErrorCodes.NONE else None,
                    execution_time_ms=execution_time_ms,
                    source_ip=source_ip,
                )
                db.add(log_entry)
                db.commit()
                _maybe_cleanup_logs()

                return result

            except ScriptLinkError as e:
                # Script raised a ScriptLink error - use its error_code
                execution_time_ms = int((time.time() - start_time) * 1000)

                # Build response with any changes made before the error
                result = wrapper.build_response()
                result.ErrorCode = e.error_code
                result.ErrorMesg = str(e)

                log_entry = RequestLog(
                    parameter=parameter,
                    option_object=input_json,
                    response_object=_option_object_to_json(result) if settings.log_request_body else None,
                    status=type(e).__name__.lower().replace("error", ""),
                    error_message=str(e),
                    execution_time_ms=execution_time_ms,
                    source_ip=source_ip,
                )
                db.add(log_entry)
                db.commit()
                _maybe_cleanup_logs()

                return result

            except Exception as e:
                # Unexpected error
                execution_time_ms = int((time.time() - start_time) * 1000)
                logger.exception(f"Script error for parameter {parameter}")

                log_entry = RequestLog(
                    parameter=parameter,
                    option_object=input_json,
                    response_object=None,
                    status="error",
                    error_message=str(e),
                    execution_time_ms=execution_time_ms,
                    source_ip=source_ip,
                )
                db.add(log_entry)
                db.commit()
                _maybe_cleanup_logs()

                optionObject.ErrorCode = ErrorCodes.ERROR if settings.script_error_blocking else ErrorCodes.ALERT
                optionObject.ErrorMesg = "LinkCentral: An unexpected error occurred. Check the server logs for details."
                return _build_minimal_response(optionObject)


def _maybe_cleanup_logs() -> None:
    """Trigger a background log cleanup if the interval has elapsed.

    The interval check is synchronous (just a datetime comparison).
    The actual DELETE runs in a background thread to avoid blocking the response.
    """
    global _last_cleanup_time

    if settings.cleanup_interval_minutes <= 0:
        return

    now = datetime.now()
    if _last_cleanup_time is not None:
        elapsed = (now - _last_cleanup_time).total_seconds() / 60
        if elapsed < settings.cleanup_interval_minutes:
            return

    # Update immediately so concurrent requests don't also trigger cleanup
    _last_cleanup_time = now

    threading.Thread(target=_run_cleanup, daemon=True).start()


def _run_cleanup() -> None:
    """Delete old request log entries in a background thread."""
    try:
        cutoff = datetime.now() - timedelta(days=settings.cleanup_retention_days)
        with get_session() as db:
            deleted = db.query(RequestLog).filter(RequestLog.created_at < cutoff).delete()
            db.commit()
            if deleted:
                logger.info(f"Cleaned up {deleted} log entries older than {settings.cleanup_retention_days} days")
    except Exception:
        logger.exception("Failed to clean up old log entries")


def _option_object_to_json(obj: OptionObject2015) -> str:
    """Convert OptionObject2015 to JSON string for storage."""
    if obj is None:
        return None

    def to_dict(o):
        if o is None:
            return None
        if hasattr(o, "__dict__"):
            result = {}
            for key, value in o.__dict__.items():
                if not key.startswith("_"):
                    if isinstance(value, list):
                        result[key] = [to_dict(item) for item in value]
                    elif hasattr(value, "__dict__"):
                        result[key] = to_dict(value)
                    else:
                        result[key] = value
            return result
        return o

    # Handle Spyne objects
    data = {
        "EntityID": obj.EntityID,
        "EpisodeNumber": obj.EpisodeNumber,
        "ErrorCode": obj.ErrorCode,
        "ErrorMesg": obj.ErrorMesg,
        "Facility": obj.Facility,
        "NamespaceName": obj.NamespaceName,
        "OptionId": obj.OptionId,
        "OptionStaffId": obj.OptionStaffId,
        "OptionUserId": obj.OptionUserId,
        "ParentNamespace": obj.ParentNamespace,
        "ServerName": obj.ServerName,
        "SystemCode": obj.SystemCode,
        "SessionToken": obj.SessionToken,
        "Forms": [],
    }

    if obj.Forms is not None:
        for form in obj.Forms:
            form_data = {
                "FormId": form.FormId,
                "MultipleIteration": form.MultipleIteration,
                "CurrentRow": _row_to_dict(form.CurrentRow) if form.CurrentRow is not None else None,
                "OtherRows": [_row_to_dict(r) for r in (form.OtherRows or [])],
            }
            data["Forms"].append(form_data)

    return json.dumps(data)


def _row_to_dict(row) -> dict:
    """Convert RowObject to dictionary."""
    if row is None:
        return None

    fields = []
    if row.Fields is not None:
        for f in row.Fields:
            fields.append({
                "FieldNumber": f.FieldNumber,
                "FieldValue": f.FieldValue,
                "Enabled": f.Enabled,
                "Lock": f.Lock,
                "Required": f.Required,
            })

    return {
        "RowId": row.RowId,
        "ParentRowId": row.ParentRowId,
        "RowAction": row.RowAction,
        "Fields": fields,
    }


def _build_minimal_response(obj: OptionObject2015) -> OptionObject2015:
    """Build a minimal response with just metadata and error info.

    Per ScriptLink spec, response should only contain modified data.
    If no modifications, return empty Forms.
    """
    obj.Forms = []
    return obj


# Create the Spyne application
# Note: No validator specified - allows elements in any order (myAvatar doesn't
# send elements in strict XSD sequence order)
soap_application = Application(
    [ScriptLinkService],
    tns=TNS,
    name=settings.service_name,
    in_protocol=Soap11(),
    out_protocol=Soap11(),
)

# Create WSGI application
class _ProxyAwareWsgiApplication(WsgiApplication):
    """WsgiApplication that rebuilds the WSDL when behind a reverse proxy.

    Spyne caches the WSDL after the first request, baking in the URL.
    When behind a proxy, different clients may reach the service via different
    addresses, so we rebuild the WSDL if the URL changes.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wsdl_url = None

    def __call__(self, req_env, start_response):
        # Stash the client IP in thread-local so RunScript can log it.
        # Prefer X-Forwarded-For (first hop) when present, fall back to REMOTE_ADDR.
        forwarded = req_env.get("HTTP_X_FORWARDED_FOR", "")
        _thread_local.source_ip = (
            forwarded.split(",")[0].strip() if forwarded else req_env.get("REMOTE_ADDR")
        )
        try:
            return super().__call__(req_env, start_response)
        finally:
            _thread_local.source_ip = None

    def handle_wsdl_request(self, req_env, start_response, url):
        if self._wsdl_url is not None and self._wsdl_url != url:
            logger.info("WSDL address changed: %s -> %s", self._wsdl_url, url)
            # Replace the address in the cached WSDL XML directly
            if self._wsdl is not None:
                self._wsdl = self._wsdl.replace(
                    self._wsdl_url.encode(), url.encode()
                )
        self._wsdl_url = url
        return super().handle_wsdl_request(req_env, start_response, url)


wsgi_application = _ProxyAwareWsgiApplication(soap_application)
