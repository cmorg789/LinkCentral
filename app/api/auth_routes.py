"""Authentication API endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import User
from app.api.auth import (
    LoginRequest,
    TokenResponse,
    UserResponse,
    authenticate_user,
    create_access_token,
    get_current_user,
)
from app.api.audit import log_audit_event, AuditActions


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    """Authenticate and receive a JWT token.

    Args:
        request: Login credentials (username and password)
        db: Database session

    Returns:
        JWT token response with expiration time

    Raises:
        HTTPException: If authentication fails
    """
    user = authenticate_user(db, request.username, request.password)

    if not user:
        # Log failed attempt
        log_audit_event(
            db=db,
            user_id=None,
            action=AuditActions.AUTH_LOGIN_FAILED,
            entity_type="user",
            entity_id=None,
            details={"username": request.username, "reason": "invalid_credentials"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        log_audit_event(
            db=db,
            user_id=user.id,
            action=AuditActions.AUTH_LOGIN_FAILED,
            entity_type="user",
            entity_id=user.id,
            details={"reason": "user_inactive"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Create token
    token, expires_at = create_access_token(user.id, user.username)

    # Log successful login
    log_audit_event(
        db=db,
        user_id=user.id,
        action=AuditActions.AUTH_LOGIN,
        entity_type="user",
        entity_id=user.id,
        details={"username": user.username},
    )

    return TokenResponse(token=token, expires_at=expires_at)


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get current authenticated user's information.

    Args:
        current_user: The authenticated user

    Returns:
        User information
    """
    return current_user


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Log out the current user.

    Note: The client should discard the token after calling this endpoint.

    Args:
        current_user: The authenticated user
        db: Database session

    Returns:
        Success message
    """
    log_audit_event(
        db=db,
        user_id=current_user.id,
        action=AuditActions.AUTH_LOGOUT,
        entity_type="user",
        entity_id=current_user.id,
        details={"username": current_user.username},
    )
    return {"message": "Logged out successfully"}
