"""Database models and connection management."""
import logging
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Generator

from sqlalchemy import Column, DateTime, Index, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)


# Models

class Base(DeclarativeBase):
    """Base class for all models."""
    pass


def _generate_uuid() -> str:
    return str(uuid.uuid4())


class RequestLog(Base):
    """Log of incoming ScriptLink requests."""

    __tablename__ = "request_log"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    parameter = Column(String(255), nullable=False)
    option_object = Column(Text, nullable=True)
    response_object = Column(Text, nullable=True)
    execution_context = Column(Text, nullable=True)
    status = Column(String(50), nullable=False)
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    source_ip = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_request_log_parameter", "parameter"),
        Index("idx_request_log_created_at", "created_at"),
        Index("idx_request_log_status", "status"),
    )


# Connection management

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database tables."""
    logger.info("Initializing database: %s", settings.database_url)
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get database session as context manager."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
