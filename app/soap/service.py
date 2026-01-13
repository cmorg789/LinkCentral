"""SOAP service implementation for ScriptLink."""
import json
import time
from datetime import datetime
from typing import Optional

from spyne import Application, Service, rpc
from spyne.decorator import srpc
from spyne.model.primitive import Unicode
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from sqlalchemy.orm import Session

from app import __version__
from app.database.connection import get_session
from app.database.models import Workflow, RequestLog
from app.soap.types import OptionObject2015, ErrorCodes, TNS


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

        Args:
            optionObject: The OptionObject2015 containing form state
            parameter: String used to route to the appropriate workflow

        Returns:
            Modified OptionObject2015
        """
        start_time = time.time()
        workflow = None
        input_json = None

        with get_session() as db:
            try:
                # Capture input JSON BEFORE execution (engine modifies option_object in-place)
                input_json = _option_object_to_json(optionObject)

                # Look up workflow by parameter
                workflow = db.query(Workflow).filter(
                    Workflow.parameter == parameter,
                    Workflow.is_active == True
                ).first()

                if workflow is None:
                    # No workflow found - always log and return error
                    execution_time_ms = int((time.time() - start_time) * 1000)

                    # Log the unconfigured request
                    log_entry = RequestLog(
                        parameter=parameter,
                        workflow_id=None,
                        option_object=input_json,
                        response_object=None,
                        status="no_workflow",
                        error_message=f"Script not configured: {parameter}",
                        execution_time_ms=execution_time_ms,
                    )
                    db.add(log_entry)
                    db.commit()

                    # Return error response
                    optionObject.ErrorCode = ErrorCodes.ALERT
                    optionObject.ErrorMesg = f"Script not configured: {parameter}"
                    return _build_minimal_response(optionObject)

                # Workflow found - execute it
                from app.workflow.engine import WorkflowEngine

                engine = WorkflowEngine(workflow, db)
                result = engine.execute(optionObject)

                execution_time_ms = int((time.time() - start_time) * 1000)

                # Log based on workflow's logging config
                _log_request(
                    db=db,
                    workflow=workflow,
                    option_object_json=input_json,
                    response_object=result,
                    execution_context=engine.get_context_json(),
                    status="success" if result.ErrorCode == ErrorCodes.NONE else "error",
                    error_message=result.ErrorMesg if result.ErrorCode != ErrorCodes.NONE else None,
                    execution_time_ms=execution_time_ms,
                )

                return result

            except Exception as e:
                execution_time_ms = int((time.time() - start_time) * 1000)

                # Log the error
                log_entry = RequestLog(
                    parameter=parameter,
                    workflow_id=workflow.id if workflow else None,
                    option_object=input_json,
                    response_object=None,
                    status="error",
                    error_message=str(e),
                    execution_time_ms=execution_time_ms,
                )
                db.add(log_entry)
                db.commit()

                # Return error response
                optionObject.ErrorCode = ErrorCodes.ERROR
                optionObject.ErrorMesg = f"Workflow error: {str(e)}"
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


def _log_request(
    db: Session,
    workflow: Workflow,
    option_object_json: str,
    response_object: OptionObject2015,
    execution_context: Optional[str],
    status: str,
    error_message: Optional[str],
    execution_time_ms: int,
) -> None:
    """Log request based on workflow's logging configuration.

    Args:
        option_object_json: Pre-serialized JSON of the original request (captured before
            workflow execution, since the engine modifies the option_object in-place).
    """
    config = json.loads(workflow.logging_config)

    if not config.get("enabled", True):
        return

    mode = config.get("mode", "last_n")
    filters = config.get("filters", {})
    storage = config.get("storage", {})

    # Check filters
    if status == "success" and not filters.get("log_on_success", True):
        return
    if status == "error" and not filters.get("log_on_error", True):
        return

    # Build log entry
    log_entry = RequestLog(
        parameter=workflow.parameter,
        workflow_id=workflow.id,
        option_object=option_object_json if storage.get("include_request", True) else None,
        response_object=_option_object_to_json(response_object) if storage.get("include_response", True) else None,
        execution_context=execution_context if storage.get("include_context", False) else None,
        status=status,
        error_message=error_message,
        execution_time_ms=execution_time_ms,
    )
    db.add(log_entry)
    db.commit()

    # Handle last_n retention
    if mode == "last_n":
        retention = config.get("retention", {})
        count = retention.get("count", 100)
        _cleanup_old_logs(db, workflow.id, keep_last=count)


def _cleanup_old_logs(db: Session, workflow_id: str, keep_last: int) -> None:
    """Delete old logs, keeping only the last N entries."""
    # Get IDs to keep
    keep_ids = db.query(RequestLog.id).filter(
        RequestLog.workflow_id == workflow_id
    ).order_by(RequestLog.created_at.desc()).limit(keep_last).subquery()

    # Delete the rest
    db.query(RequestLog).filter(
        RequestLog.workflow_id == workflow_id,
        ~RequestLog.id.in_(keep_ids)
    ).delete(synchronize_session=False)
    db.commit()


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
