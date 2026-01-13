"""Database connection management."""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.config import settings
from app.database.models import Base


# Create engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _run_migrations() -> None:
    """Run manual migrations for schema changes not handled by create_all."""
    with engine.connect() as conn:
        # Check if test_fixtures column exists in workflows table
        result = conn.execute(text("PRAGMA table_info(workflows)"))
        columns = [row[1] for row in result.fetchall()]

        if "test_fixtures" not in columns:
            conn.execute(text(
                "ALTER TABLE workflows ADD COLUMN test_fixtures TEXT NOT NULL DEFAULT '[]'"
            ))
            conn.commit()


def init_db() -> None:
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    _run_migrations()


def get_db() -> Generator[Session, None, None]:
    """Get database session as dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
