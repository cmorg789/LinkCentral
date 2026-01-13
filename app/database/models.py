"""SQLAlchemy database models."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


class Workflow(Base):
    """Workflow definition."""

    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    parameter = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    nodes = Column(Text, nullable=False, default="[]")  # JSON
    edges = Column(Text, nullable=False, default="[]")  # JSON
    logging_config = Column(
        Text,
        nullable=False,
        default='{"enabled":true,"mode":"last_n","retention":{"count":100}}'
    )  # JSON
    test_fixtures = Column(Text, nullable=False, default="[]")  # JSON - test data for simulation
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=True)
    updated_by = Column(String(255), nullable=True)

    # Relationship
    request_logs = relationship("RequestLog", back_populates="workflow")

    def __repr__(self) -> str:
        return f"<Workflow(id={self.id}, name={self.name}, parameter={self.parameter})>"


class RequestLog(Base):
    """Log of incoming ScriptLink requests."""

    __tablename__ = "request_log"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    parameter = Column(String(255), nullable=False)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=True)
    option_object = Column(Text, nullable=True)  # JSON - NULL if storage disabled
    response_object = Column(Text, nullable=True)  # JSON - NULL if storage disabled
    execution_context = Column(Text, nullable=True)  # JSON - NULL unless debug enabled
    status = Column(String(50), nullable=False)  # 'success', 'error', 'no_workflow'
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    source_ip = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    workflow = relationship("Workflow", back_populates="request_logs")

    __table_args__ = (
        Index("idx_request_log_parameter", "parameter"),
        Index("idx_request_log_workflow_id", "workflow_id"),
        Index("idx_request_log_created_at", "created_at"),
        Index("idx_request_log_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<RequestLog(id={self.id}, parameter={self.parameter}, status={self.status})>"


class User(Base):
    """User account for web interface."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"


class AuditLog(Base):
    """Audit log for significant actions."""

    __tablename__ = "audit_log"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)  # 'workflow.create', 'workflow.update', etc.
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(String(36), nullable=True)
    details = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action})>"


class Connection(Base):
    """External database connection configuration."""

    __tablename__ = "connections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), unique=True, nullable=False)
    driver = Column(String(50), nullable=False)  # 'iris', 'mssql', etc.
    connection_string_encrypted = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Connection(id={self.id}, name={self.name}, driver={self.driver})>"
