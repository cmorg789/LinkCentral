"""Audit logging service."""
import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.database.models import AuditLog


class AuditActions:
    """Standard audit action identifiers."""

    # Authentication
    AUTH_LOGIN = "auth.login"
    AUTH_LOGIN_FAILED = "auth.login_failed"
    AUTH_LOGOUT = "auth.logout"

    # Workflows
    WORKFLOW_CREATE = "workflow.create"
    WORKFLOW_UPDATE = "workflow.update"
    WORKFLOW_DELETE = "workflow.delete"
    WORKFLOW_LOGGING_UPDATE = "workflow.logging_update"

    # Connections
    CONNECTION_CREATE = "connection.create"
    CONNECTION_UPDATE = "connection.update"
    CONNECTION_DELETE = "connection.delete"
    CONNECTION_TEST = "connection.test"

    # Settings
    SETTINGS_UPDATE = "settings.update"

    # Requests
    REQUEST_DELETE = "request.delete"
    REQUEST_CLEANUP = "request.cleanup"

    # Setup
    SETUP_CREATE_ADMIN = "setup.create_admin"

    # Users
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_PASSWORD_RESET = "user.password_reset"
    USER_DELETE = "user.delete"


def log_audit_event(
    db: Session,
    action: str,
    user_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> AuditLog:
    """Log an audit event to the database.

    Args:
        db: Database session
        action: Action identifier (e.g., 'workflow.create', 'auth.login')
        user_id: ID of the user performing the action
        entity_type: Type of entity affected (e.g., 'workflow', 'connection')
        entity_id: ID of the entity affected
        details: Additional details as a dictionary

    Returns:
        The created AuditLog entry
    """
    audit_entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=json.dumps(details) if details else None,
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    return audit_entry
