"""SOAP service implementation for ScriptLink."""
import io
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime
from pathlib import Path
from typing import Optional

from spyne import Application, Service, rpc
from spyne.decorator import srpc
from spyne.model.primitive import Unicode
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from sqlalchemy.orm import Session

from app import __version__
from app.config import settings
from app.db import get_session, RequestLog
from app.soap.types import OptionObject2015, ErrorCodes, TNS
from app.scriptlink import ScriptRouter, OptionObjectWrapper, ScriptLinkError

logger = logging.getLogger(__name__)

# Initialize the script router
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
DATA_DIR = Path(__file__).parent.parent.parent / "data"
_router = ScriptRouter(SCRIPTS_DIR, DATA_DIR)


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

        with (get_session() as db):
            # Create wrapper for Pythonic access
            wrapper = OptionObjectWrapper(optionObject)
            input_json = json.dumps(wrapper.to_dict())

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
                    )
                    db.add(log_entry)
                    db.commit()

                    # Return error response
                    optionObject.ErrorCode = ErrorCodes.ALERT
                    optionObject.ErrorMesg = f"Script not configured: {parameter}"
                    return _build_minimal_response(optionObject)

                # Script found - execute with stdout capture and timeout
                def run_script():
                    captured = io.StringIO()
                    old_out = sys.stdout
                    try:
                        sys.stdout = captured
                        res = handler(wrapper)
                        return res, captured.getvalue()
                    finally:
                        sys.stdout = old_out

                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_script)
                    try:
                        result, script_output = future.result(timeout=settings.script_timeout)
                    except FuturesTimeoutError:
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
                    response_object=_option_object_to_json(result),
                    execution_context=json.dumps({"diff": diff, "output": script_output}) if (diff or script_output) else None,
                    status="success" if result.ErrorCode == ErrorCodes.NONE else "error",
                    error_message=result.ErrorMesg if result.ErrorCode != ErrorCodes.NONE else None,
                    execution_time_ms=execution_time_ms,
                )
                db.add(log_entry)
                db.commit()

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
                    response_object=_option_object_to_json(result),
                    status=type(e).__name__.lower().replace("error", ""),
                    error_message=str(e),
                    execution_time_ms=execution_time_ms,
                )
                db.add(log_entry)
                db.commit()

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
                )
                db.add(log_entry)
                db.commit()


                optionObject.ErrorCode = ErrorCodes.ERROR if settings.script_error_blocking else ErrorCodes.ALERT
                optionObject.ErrorMesg = f"Script error: {str(e)}"
                return _build_minimal_response(optionObject)


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
    name="LinkCentral",
    in_protocol=Soap11(),
    out_protocol=Soap11(),
)

# Create WSGI application
wsgi_application = WsgiApplication(soap_application)
