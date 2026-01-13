"""Setup routes for first-time configuration."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.audit import AuditActions, log_audit_event
from app.api.auth import hash_password
from app.database.connection import get_db
from app.database.models import User


router = APIRouter(prefix="/setup", tags=["setup"])


class SetupStatusResponse(BaseModel):
    """Response for setup status check."""
    needs_setup: bool


class SetupCreateRequest(BaseModel):
    """Request body for creating first admin user."""
    username: str
    password: str


class SetupCreateResponse(BaseModel):
    """Response for admin creation."""
    success: bool
    message: str


@router.get("/status", response_model=SetupStatusResponse)
def get_setup_status(db: Session = Depends(get_db)):
    """Check if first-time setup is needed.

    Returns needs_setup=true if no users exist in the database.
    This endpoint does not require authentication.
    """
    user_count = db.query(User).count()
    return SetupStatusResponse(needs_setup=user_count == 0)


@router.post("/create-admin", response_model=SetupCreateResponse)
def create_first_admin(
    request: SetupCreateRequest,
    db: Session = Depends(get_db),
):
    """Create the first admin user during initial setup.

    This endpoint only works when no users exist in the database.
    It does not require authentication.
    """
    # Check if setup is still needed
    user_count = db.query(User).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup has already been completed. Users already exist.",
        )

    # Validate username
    if not request.username or not request.username.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is required.",
        )

    # Validate password
    if not request.password or len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters.",
        )

    # Create the admin user with race condition protection
    user = User(
        username=request.username.strip(),
        password_hash=hash_password(request.password),
        is_active=True,
    )

    try:
        db.add(user)
        db.flush()  # Flush to detect constraint violations before commit

        # Re-check user count after flush to prevent race conditions
        user_count = db.query(User).count()
        if user_count > 1:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Setup has already been completed. Users already exist.",
            )

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup has already been completed or username already exists.",
        )

    # Log the setup event
    log_audit_event(
        db=db,
        action=AuditActions.SETUP_CREATE_ADMIN,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        details={"username": user.username},
    )

    return SetupCreateResponse(
        success=True,
        message=f"Admin user '{user.username}' created successfully.",
    )
