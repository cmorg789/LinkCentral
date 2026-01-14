"""REST API endpoints for workflow and request management."""
import json
import logging
import ssl
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query

logger = logging.getLogger(__name__)
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Workflow, RequestLog, Connection, User, AuditLog
from app.database.encryption import encrypt_password, decrypt_password
from app.api.auth import get_current_user, get_optional_user
from app.api.audit import log_audit_event, AuditActions
from app.workflow.traced_engine import TracedWorkflowEngine
from app.workflow.option_object_helpers import option_object_to_dict, dict_to_option_object, build_delta_dict


router = APIRouter()


# ============================================================================
# Pydantic Models
# ============================================================================

class WorkflowBase(BaseModel):
    """Base workflow schema."""
    name: str
    parameter: str
    description: Optional[str] = None
    is_active: bool = True


class WorkflowCreate(WorkflowBase):
    """Schema for creating a workflow."""
    nodes: str = "[]"  # JSON string
    edges: str = "[]"  # JSON string
    logging_config: str = '{"enabled":true,"mode":"last_n","retention":{"count":100}}'


class WorkflowUpdate(BaseModel):
    """Schema for updating a workflow."""
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[str] = None
    edges: Optional[str] = None
    logging_config: Optional[str] = None
    is_active: Optional[bool] = None


class WorkflowResponse(WorkflowBase):
    """Schema for workflow response."""
    id: str
    nodes: str
    edges: str
    logging_config: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RequestLogResponse(BaseModel):
    """Schema for request log response."""
    id: str
    parameter: str
    workflow_id: Optional[str]
    status: str
    error_message: Optional[str]
    execution_time_ms: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class RequestLogDetailResponse(RequestLogResponse):
    """Schema for detailed request log response."""
    option_object: Optional[str]
    response_object: Optional[str]
    execution_context: Optional[str]


class UnconfiguredParameter(BaseModel):
    """Schema for unconfigured parameter summary."""
    parameter: str
    count: int
    last_seen: datetime
    latest_request_id: str


class LoggingConfigUpdate(BaseModel):
    """Schema for updating logging configuration."""
    enabled: Optional[bool] = None
    mode: Optional[str] = None
    retention: Optional[dict] = None
    filters: Optional[dict] = None
    storage: Optional[dict] = None


class ConnectionCreate(BaseModel):
    """Schema for creating a database connection."""
    name: str
    driver: str  # 'iris', 'mssql', 'postgresql', etc.
    host: str
    port: int
    database: str
    username: str
    password: str
    # SSL settings
    ssl_mode: str = "disabled"  # 'disabled', 'cert_none', 'cert_optional', 'cert_required'
    ssl_check_hostname: bool = True


class ConnectionUpdate(BaseModel):
    """Schema for updating a database connection."""
    name: Optional[str] = None
    driver: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None  # Only updated if provided
    # SSL settings
    ssl_mode: Optional[str] = None
    ssl_check_hostname: Optional[bool] = None


class ConnectionResponse(BaseModel):
    """Schema for connection response (password hidden)."""
    id: str
    name: str
    driver: str
    host: str
    port: int
    database: str
    username: str
    ssl_mode: str
    ssl_check_hostname: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConnectionTestResult(BaseModel):
    """Schema for connection test result."""
    success: bool
    message: str


class AppSettingsResponse(BaseModel):
    """Schema for app settings response."""
    cleanup_interval_minutes: int


class AppSettingsUpdate(BaseModel):
    """Schema for updating app settings."""
    cleanup_interval_minutes: Optional[int] = None


# ============================================================================
# Simulation & Test Fixture Models
# ============================================================================

class TestFixture(BaseModel):
    """Schema for a test fixture."""
    id: str
    name: str
    option_object: Dict[str, Any]
    created_at: str
    source: Optional[str] = None  # "request_log", "manual"
    request_log_id: Optional[str] = None


class TestFixtureCreate(BaseModel):
    """Schema for creating a test fixture."""
    name: str
    option_object: Dict[str, Any]


class SimulationRequest(BaseModel):
    """Schema for simulation request."""
    fixture_id: str
    nodes: str  # JSON string of current nodes (may differ from saved)
    edges: str  # JSON string of current edges


class SimulationNodeResult(BaseModel):
    """Schema for a single node's execution result."""
    node_id: str
    node_type: str
    executed: bool
    execution_order: Optional[int] = None
    output_port: Optional[str] = None
    output_values: Dict[str, Any] = {}
    error: Optional[str] = None


class SimulationResponse(BaseModel):
    """Schema for simulation response."""
    success: bool
    input_option_object: Dict[str, Any]
    output_option_object: Dict[str, Any]
    output_delta: Dict[str, Any]  # Only the modified fields (ScriptLink response format)
    variables: Dict[str, Any]
    execution_trace: List[SimulationNodeResult]
    error: Optional[str] = None
    execution_time_ms: int


# ============================================================================
# Workflow Endpoints
# ============================================================================

@router.get("/workflows", response_model=List[WorkflowResponse])
def list_workflows(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all workflows."""
    workflows = db.query(Workflow).offset(skip).limit(limit).all()
    return workflows


@router.post("/workflows", response_model=WorkflowResponse, status_code=201)
def create_workflow(
    workflow: WorkflowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new workflow."""
    # Check for duplicate parameter
    existing = db.query(Workflow).filter(Workflow.parameter == workflow.parameter).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Workflow with parameter '{workflow.parameter}' already exists")

    # Validate JSON fields
    try:
        json.loads(workflow.nodes)
        json.loads(workflow.edges)
        json.loads(workflow.logging_config)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    db_workflow = Workflow(**workflow.model_dump())
    db_workflow.created_by = current_user.username
    db_workflow.updated_by = current_user.username
    db.add(db_workflow)
    db.commit()
    db.refresh(db_workflow)

    # Audit log
    log_audit_event(
        db=db,
        user_id=current_user.id,
        action=AuditActions.WORKFLOW_CREATE,
        entity_type="workflow",
        entity_id=db_workflow.id,
        details={"name": db_workflow.name, "parameter": db_workflow.parameter},
    )

    return db_workflow


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
):
    """Get a workflow by ID."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.put("/workflows/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: str,
    workflow_update: WorkflowUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a workflow."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    update_data = workflow_update.model_dump(exclude_unset=True)

    # Validate JSON fields if provided
    for field in ["nodes", "edges", "logging_config"]:
        if field in update_data:
            try:
                json.loads(update_data[field])
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON in {field}: {str(e)}")

    # Track changes for audit
    changes = {}
    for key, value in update_data.items():
        old_value = getattr(workflow, key)
        if old_value != value:
            # Truncate large values for audit log
            changes[key] = {
                "old": str(old_value)[:100] if old_value else None,
                "new": str(value)[:100] if value else None,
            }

    for key, value in update_data.items():
        setattr(workflow, key, value)

    workflow.updated_at = datetime.utcnow()
    workflow.updated_by = current_user.username
    db.commit()
    db.refresh(workflow)

    # Audit log
    log_audit_event(
        db=db,
        user_id=current_user.id,
        action=AuditActions.WORKFLOW_UPDATE,
        entity_type="workflow",
        entity_id=workflow.id,
        details={"name": workflow.name, "changes": changes},
    )

    return workflow


@router.delete("/workflows/{workflow_id}", status_code=204)
def delete_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a workflow."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Capture info before deletion for audit
    workflow_info = {"name": workflow.name, "parameter": workflow.parameter}

    db.delete(workflow)
    db.commit()

    # Audit log
    log_audit_event(
        db=db,
        user_id=current_user.id,
        action=AuditActions.WORKFLOW_DELETE,
        entity_type="workflow",
        entity_id=workflow_id,
        details=workflow_info,
    )

    return None


@router.patch("/workflows/{workflow_id}/logging", response_model=WorkflowResponse)
def update_workflow_logging(
    workflow_id: str,
    config_update: LoggingConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update workflow logging configuration."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Parse existing config
    current_config = json.loads(workflow.logging_config)
    old_config = current_config.copy()

    # Update with new values
    update_data = config_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if isinstance(value, dict) and key in current_config and isinstance(current_config[key], dict):
            current_config[key].update(value)
        else:
            current_config[key] = value

    workflow.logging_config = json.dumps(current_config)
    workflow.updated_at = datetime.utcnow()
    workflow.updated_by = current_user.username
    db.commit()
    db.refresh(workflow)

    # Audit log
    log_audit_event(
        db=db,
        user_id=current_user.id,
        action=AuditActions.WORKFLOW_LOGGING_UPDATE,
        entity_type="workflow",
        entity_id=workflow.id,
        details={"name": workflow.name, "old_config": old_config, "new_config": current_config},
    )

    return workflow


# ============================================================================
# Workflow Simulation & Test Fixtures
# ============================================================================

@router.get("/workflows/{workflow_id}/fixtures", response_model=List[TestFixture])
def list_test_fixtures(
    workflow_id: str,
    db: Session = Depends(get_db),
):
    """List all test fixtures for a workflow."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    fixtures = json.loads(workflow.test_fixtures or "[]")
    return fixtures


@router.post("/workflows/{workflow_id}/fixtures", response_model=TestFixture, status_code=201)
def create_test_fixture(
    workflow_id: str,
    fixture: TestFixtureCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new test fixture for a workflow."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    fixtures = json.loads(workflow.test_fixtures or "[]")

    new_fixture = {
        "id": str(uuid.uuid4()),
        "name": fixture.name,
        "option_object": fixture.option_object,
        "created_at": datetime.utcnow().isoformat(),
        "source": "manual",
    }

    fixtures.append(new_fixture)
    workflow.test_fixtures = json.dumps(fixtures)
    workflow.updated_at = datetime.utcnow()
    db.commit()

    return new_fixture


@router.post("/workflows/{workflow_id}/fixtures/from-request/{request_id}", response_model=TestFixture, status_code=201)
def create_fixture_from_request(
    workflow_id: str,
    request_id: str,
    name: str = Query(..., description="Name for the new fixture"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a test fixture from an existing request log entry."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    request_log = db.query(RequestLog).filter(RequestLog.id == request_id).first()
    if not request_log:
        raise HTTPException(status_code=404, detail="Request log not found")

    if not request_log.option_object:
        raise HTTPException(status_code=400, detail="Request log has no stored option object")

    option_object = json.loads(request_log.option_object)
    fixtures = json.loads(workflow.test_fixtures or "[]")

    new_fixture = {
        "id": str(uuid.uuid4()),
        "name": name,
        "option_object": option_object,
        "created_at": datetime.utcnow().isoformat(),
        "source": "request_log",
        "request_log_id": request_id,
    }

    fixtures.append(new_fixture)
    workflow.test_fixtures = json.dumps(fixtures)
    workflow.updated_at = datetime.utcnow()
    db.commit()

    return new_fixture


@router.put("/workflows/{workflow_id}/fixtures/{fixture_id}", response_model=TestFixture)
def update_test_fixture(
    workflow_id: str,
    fixture_id: str,
    fixture_update: TestFixtureCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a test fixture."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    fixtures = json.loads(workflow.test_fixtures or "[]")

    # Find and update the fixture
    for i, f in enumerate(fixtures):
        if f["id"] == fixture_id:
            fixtures[i]["name"] = fixture_update.name
            fixtures[i]["option_object"] = fixture_update.option_object
            workflow.test_fixtures = json.dumps(fixtures)
            workflow.updated_at = datetime.utcnow()
            db.commit()
            return fixtures[i]

    raise HTTPException(status_code=404, detail="Fixture not found")


@router.delete("/workflows/{workflow_id}/fixtures/{fixture_id}", status_code=204)
def delete_test_fixture(
    workflow_id: str,
    fixture_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a test fixture."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    fixtures = json.loads(workflow.test_fixtures or "[]")
    original_len = len(fixtures)

    fixtures = [f for f in fixtures if f["id"] != fixture_id]

    if len(fixtures) == original_len:
        raise HTTPException(status_code=404, detail="Fixture not found")

    workflow.test_fixtures = json.dumps(fixtures)
    workflow.updated_at = datetime.utcnow()
    db.commit()

    return None


@router.post("/workflows/{workflow_id}/simulate", response_model=SimulationResponse)
def simulate_workflow(
    workflow_id: str,
    request: SimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Simulate workflow execution with a test fixture.

    This endpoint runs the workflow against a test fixture and returns
    detailed execution trace, including which nodes executed, their outputs,
    and the final state of all variables.
    """
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Find the fixture
    fixtures = json.loads(workflow.test_fixtures or "[]")
    fixture = next((f for f in fixtures if f["id"] == request.fixture_id), None)
    if not fixture:
        raise HTTPException(status_code=404, detail="Fixture not found")

    # Create a temporary workflow object with the current nodes/edges
    # This allows testing unsaved changes
    temp_workflow = Workflow(
        id=workflow.id,
        name=workflow.name,
        parameter=workflow.parameter,
        nodes=request.nodes,
        edges=request.edges,
    )

    # Convert fixture option_object to OptionObject2015
    input_dict = fixture["option_object"]

    start_time = time.time()
    try:
        option_object = dict_to_option_object(input_dict)

        # Execute with tracing
        engine = TracedWorkflowEngine(temp_workflow, db)
        result_object = engine.execute(option_object)

        execution_time_ms = int((time.time() - start_time) * 1000)

        # Build delta response showing only modified fields
        output_delta = build_delta_dict(
            engine.get_modified_fields(),
            result_object
        )

        return SimulationResponse(
            success=True,
            input_option_object=input_dict,
            output_option_object=option_object_to_dict(result_object),
            output_delta=output_delta,
            variables=engine.get_variables(),
            execution_trace=[
                SimulationNodeResult(**record)
                for record in engine.get_execution_trace()
            ],
            error=None,
            execution_time_ms=execution_time_ms,
        )
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        return SimulationResponse(
            success=False,
            input_option_object=input_dict,
            output_option_object={},
            output_delta={},
            variables={},
            execution_trace=[],
            error=str(e),
            execution_time_ms=execution_time_ms,
        )


# ============================================================================
# Request Log Endpoints
# ============================================================================

@router.get("/requests", response_model=List[RequestLogResponse])
def list_requests(
    workflow_id: Optional[str] = Query(None),
    parameter: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List request logs with optional filters."""
    query = db.query(RequestLog)

    if workflow_id:
        query = query.filter(RequestLog.workflow_id == workflow_id)
    if parameter:
        query = query.filter(RequestLog.parameter == parameter)
    if status:
        query = query.filter(RequestLog.status == status)

    requests = query.order_by(RequestLog.created_at.desc()).offset(offset).limit(limit).all()
    return requests


@router.get("/requests/unconfigured", response_model=List[UnconfiguredParameter])
def list_unconfigured_parameters(
    db: Session = Depends(get_db),
):
    """List parameters that have no configured workflow."""
    # Get aggregates per parameter
    aggregates = db.query(
        RequestLog.parameter,
        func.count(RequestLog.id).label("count"),
        func.max(RequestLog.created_at).label("last_seen"),
    ).filter(
        RequestLog.status == "no_workflow"
    ).group_by(
        RequestLog.parameter
    ).all()

    # For each parameter, get the latest request ID
    results = []
    for agg in aggregates:
        latest_request = db.query(RequestLog.id).filter(
            RequestLog.parameter == agg.parameter,
            RequestLog.status == "no_workflow"
        ).order_by(
            RequestLog.created_at.desc()
        ).first()

        results.append(UnconfiguredParameter(
            parameter=agg.parameter,
            count=agg.count,
            last_seen=agg.last_seen,
            latest_request_id=latest_request.id if latest_request else "",
        ))

    return results


@router.delete("/requests/unconfigured/{parameter}", status_code=200)
def delete_unconfigured_parameter(
    parameter: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete all unconfigured requests for a parameter."""
    count = db.query(RequestLog).filter(
        RequestLog.parameter == parameter,
        RequestLog.status == "no_workflow"
    ).delete(synchronize_session=False)

    db.commit()

    # Audit log
    log_audit_event(
        db=db,
        user_id=current_user.id,
        action=AuditActions.REQUEST_DELETE,
        entity_type="unconfigured_parameter",
        entity_id=parameter,
        details={"deleted_count": count},
    )

    return {"deleted_count": count}


@router.get("/requests/{request_id}", response_model=RequestLogDetailResponse)
def get_request(
    request_id: str,
    db: Session = Depends(get_db),
):
    """Get detailed request log by ID."""
    request_log = db.query(RequestLog).filter(RequestLog.id == request_id).first()
    if not request_log:
        raise HTTPException(status_code=404, detail="Request not found")
    return request_log


@router.delete("/requests/{request_id}", status_code=204)
def delete_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a request log entry."""
    request_log = db.query(RequestLog).filter(RequestLog.id == request_id).first()
    if not request_log:
        raise HTTPException(status_code=404, detail="Request not found")

    # Capture info for audit
    request_info = {"parameter": request_log.parameter, "status": request_log.status}

    db.delete(request_log)
    db.commit()

    # Audit log
    log_audit_event(
        db=db,
        user_id=current_user.id,
        action=AuditActions.REQUEST_DELETE,
        entity_type="request",
        entity_id=request_id,
        details=request_info,
    )

    return None


@router.delete("/requests/cleanup", status_code=200)
def trigger_cleanup(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger manual cleanup per retention policies."""
    workflows = db.query(Workflow).all()
    deleted_count = 0

    for workflow in workflows:
        config = json.loads(workflow.logging_config)

        if not config.get("enabled", True):
            # Delete all logs for disabled logging
            count = db.query(RequestLog).filter(
                RequestLog.workflow_id == workflow.id
            ).delete(synchronize_session=False)
            deleted_count += count
            continue

        mode = config.get("mode", "last_n")
        retention = config.get("retention", {})

        if mode == "last_n":
            keep_count = retention.get("count", 100)
            # Get IDs to keep
            keep_subquery = db.query(RequestLog.id).filter(
                RequestLog.workflow_id == workflow.id
            ).order_by(
                RequestLog.created_at.desc()
            ).limit(keep_count).subquery()

            # Delete older logs
            count = db.query(RequestLog).filter(
                RequestLog.workflow_id == workflow.id,
                ~RequestLog.id.in_(keep_subquery)
            ).delete(synchronize_session=False)
            deleted_count += count

        elif mode == "none":
            count = db.query(RequestLog).filter(
                RequestLog.workflow_id == workflow.id
            ).delete(synchronize_session=False)
            deleted_count += count

    db.commit()

    # Audit log
    log_audit_event(
        db=db,
        user_id=current_user.id,
        action=AuditActions.REQUEST_CLEANUP,
        entity_type="request",
        entity_id=None,
        details={"deleted_count": deleted_count},
    )

    return {"deleted_count": deleted_count}


# ============================================================================
# Connection Endpoints
# ============================================================================

def _parse_connection_data(connection: Connection) -> dict:
    """Parse stored connection data from JSON."""
    data = json.loads(connection.connection_string_encrypted)
    return {
        "id": connection.id,
        "name": connection.name,
        "driver": connection.driver,
        "host": data.get("host", ""),
        "port": data.get("port", 0),
        "database": data.get("database", ""),
        "username": data.get("username", ""),
        "ssl_mode": data.get("ssl_mode", "disabled"),
        "ssl_check_hostname": data.get("ssl_check_hostname", True),
        "is_active": connection.is_active,
        "created_at": connection.created_at,
        "updated_at": connection.updated_at,
    }


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
    from sqlalchemy import URL

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


@router.get("/connections", response_model=List[ConnectionResponse])
def list_connections(
    db: Session = Depends(get_db),
):
    """List all database connections (passwords hidden)."""
    connections = db.query(Connection).all()
    return [_parse_connection_data(c) for c in connections]


@router.post("/connections", response_model=ConnectionResponse, status_code=201)
def create_connection(
    conn: ConnectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new database connection."""
    # Check for duplicate name
    existing = db.query(Connection).filter(Connection.name == conn.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Connection with name '{conn.name}' already exists")

    # Store connection data as JSON with encrypted password
    conn_data = {
        "host": conn.host,
        "port": conn.port,
        "database": conn.database,
        "username": conn.username,
        "password_encrypted": encrypt_password(conn.password),
        "ssl_mode": conn.ssl_mode,
        "ssl_check_hostname": conn.ssl_check_hostname,
    }

    db_connection = Connection(
        name=conn.name,
        driver=conn.driver,
        connection_string_encrypted=json.dumps(conn_data),
    )
    db.add(db_connection)
    db.commit()
    db.refresh(db_connection)

    # Audit log
    log_audit_event(
        db=db,
        user_id=current_user.id,
        action=AuditActions.CONNECTION_CREATE,
        entity_type="connection",
        entity_id=db_connection.id,
        details={"name": conn.name, "driver": conn.driver, "host": conn.host},
    )

    return _parse_connection_data(db_connection)


@router.get("/connections/{connection_id}", response_model=ConnectionResponse)
def get_connection(
    connection_id: str,
    db: Session = Depends(get_db),
):
    """Get a connection by ID (password hidden)."""
    connection = db.query(Connection).filter(Connection.id == connection_id).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    return _parse_connection_data(connection)


@router.put("/connections/{connection_id}", response_model=ConnectionResponse)
def update_connection(
    connection_id: str,
    conn_update: ConnectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a database connection."""
    connection = db.query(Connection).filter(Connection.id == connection_id).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Check for duplicate name if changing
    if conn_update.name and conn_update.name != connection.name:
        existing = db.query(Connection).filter(Connection.name == conn_update.name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Connection with name '{conn_update.name}' already exists")

    # Parse existing data
    conn_data = json.loads(connection.connection_string_encrypted)
    old_name = connection.name

    # Update fields
    update_data = conn_update.model_dump(exclude_unset=True)

    # Track changes for audit
    changes = list(update_data.keys())
    if "password" in changes:
        changes.remove("password")
        changes.append("password (changed)")

    if "name" in update_data:
        connection.name = update_data["name"]
    if "driver" in update_data:
        connection.driver = update_data["driver"]
    if "host" in update_data:
        conn_data["host"] = update_data["host"]
    if "port" in update_data:
        conn_data["port"] = update_data["port"]
    if "database" in update_data:
        conn_data["database"] = update_data["database"]
    if "username" in update_data:
        conn_data["username"] = update_data["username"]
    if "password" in update_data:
        conn_data["password_encrypted"] = encrypt_password(update_data["password"])
    if "ssl_mode" in update_data:
        conn_data["ssl_mode"] = update_data["ssl_mode"]
    if "ssl_check_hostname" in update_data:
        conn_data["ssl_check_hostname"] = update_data["ssl_check_hostname"]

    connection.connection_string_encrypted = json.dumps(conn_data)
    connection.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(connection)

    # Audit log
    log_audit_event(
        db=db,
        user_id=current_user.id,
        action=AuditActions.CONNECTION_UPDATE,
        entity_type="connection",
        entity_id=connection.id,
        details={"name": old_name, "updated_fields": changes},
    )

    return _parse_connection_data(connection)


@router.delete("/connections/{connection_id}", status_code=204)
def delete_connection(
    connection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a database connection."""
    connection = db.query(Connection).filter(Connection.id == connection_id).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Capture info for audit
    connection_info = {"name": connection.name, "driver": connection.driver}

    db.delete(connection)
    db.commit()

    # Audit log
    log_audit_event(
        db=db,
        user_id=current_user.id,
        action=AuditActions.CONNECTION_DELETE,
        entity_type="connection",
        entity_id=connection_id,
        details=connection_info,
    )

    return None


@router.post("/connections/{connection_id}/test", response_model=ConnectionTestResult)
def test_connection(
    connection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Test a database connection."""
    from sqlalchemy import create_engine, text

    connection = db.query(Connection).filter(Connection.id == connection_id).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Parse connection data
    conn_data = json.loads(connection.connection_string_encrypted)
    password = decrypt_password(conn_data.get("password_encrypted", ""))

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

        # Add timeout arg for drivers that support it
        # IRIS doesn't support connect_timeout in connect_args
        if connection.driver != "iris":
            connect_args["connect_timeout"] = 5

        # Try to connect with limited pool
        engine = create_engine(
            conn_url,
            connect_args=connect_args,
            pool_size=1,
            max_overflow=0
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        return ConnectionTestResult(success=True, message="Connection successful")

    except ValueError as e:
        logger.error("Connection test failed (ValueError): %s", str(e))
        return ConnectionTestResult(success=False, message=str(e))
    except Exception as e:
        logger.exception("Connection test failed for '%s' at '%s' (%s://%s:%s/%s)",
                         conn_data["username"],
                        connection.name,
                        connection.driver,
                        conn_data["host"],
                        conn_data["port"],
                        conn_data["database"])
        return ConnectionTestResult(success=False, message=f"Connection failed: {str(e)}")
    finally:
        if engine:
            engine.dispose()


# ============================================================================
# App Settings Endpoints
# ============================================================================

@router.get("/settings", response_model=AppSettingsResponse)
def get_settings():
    """Get application settings (runtime-safe settings only)."""
    from app.config import settings
    return AppSettingsResponse(
        cleanup_interval_minutes=settings.cleanup_interval_minutes,
    )


@router.put("/settings", response_model=AppSettingsResponse)
def update_settings(
    settings_update: AppSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update application settings at runtime.

    Note: Changes are applied in-memory and will not persist across restarts.
    """
    from app.config import settings

    update_data = settings_update.model_dump(exclude_unset=True)
    old_values = {}

    if "cleanup_interval_minutes" in update_data:
        old_values["cleanup_interval_minutes"] = settings.cleanup_interval_minutes
        # Update the settings singleton in memory
        object.__setattr__(settings, "cleanup_interval_minutes", update_data["cleanup_interval_minutes"])

    # Audit log
    log_audit_event(
        db=db,
        user_id=current_user.id,
        action=AuditActions.SETTINGS_UPDATE,
        entity_type="settings",
        entity_id=None,
        details={"old_values": old_values, "new_values": update_data},
    )

    return AppSettingsResponse(
        cleanup_interval_minutes=settings.cleanup_interval_minutes,
    )


# ============================================================================
# Audit Log Endpoints
# ============================================================================

class AuditLogResponse(BaseModel):
    """Schema for audit log response."""
    id: str
    user_id: Optional[str]
    action: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    details: Optional[str]  # JSON string
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/audit-logs", response_model=List[AuditLogResponse])
def list_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action type"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List audit log entries."""
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    return logs
