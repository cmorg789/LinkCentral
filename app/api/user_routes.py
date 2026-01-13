"""User management routes."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.audit import AuditActions, log_audit_event
from app.api.auth import get_current_user, hash_password
from app.database.connection import get_db
from app.database.models import User


router = APIRouter(prefix="/users", tags=["users"])


class UserResponse(BaseModel):
    """User response model."""
    id: str
    username: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """Request body for creating a user."""
    username: str
    password: str


class UserUpdate(BaseModel):
    """Request body for updating a user."""
    username: Optional[str] = None
    is_active: Optional[bool] = None


class PasswordReset(BaseModel):
    """Request body for resetting a password."""
    password: str


@router.get("", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all users."""
    users = db.query(User).order_by(User.username).all()
    return users


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    request: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new user."""
    # Validate username
    if not request.username or not request.username.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is required.",
        )

    # Check for duplicate username
    existing = db.query(User).filter(User.username == request.username.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{request.username}' already exists.",
        )

    # Validate password
    if not request.password or len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters.",
        )

    # Create user
    user = User(
        username=request.username.strip(),
        password_hash=hash_password(request.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Log audit event
    log_audit_event(
        db=db,
        action=AuditActions.USER_CREATE,
        user_id=current_user.id,
        entity_type="user",
        entity_id=user.id,
        details={"username": user.username},
    )

    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    request: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a user's username or active status."""
    # Find user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    changes = {}

    # Update username if provided
    if request.username is not None:
        username = request.username.strip()
        if not username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username cannot be empty.",
            )
        # Check for duplicate (excluding current user)
        existing = db.query(User).filter(
            User.username == username,
            User.id != user_id,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{username}' already exists.",
            )
        if user.username != username:
            changes["username"] = {"from": user.username, "to": username}
            user.username = username

    # Update active status if provided
    if request.is_active is not None:
        # Prevent deactivating yourself
        if user_id == current_user.id and not request.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account.",
            )
        if user.is_active != request.is_active:
            changes["is_active"] = {"from": user.is_active, "to": request.is_active}
            user.is_active = request.is_active

    if changes:
        db.commit()
        db.refresh(user)

        # Log audit event
        log_audit_event(
            db=db,
            action=AuditActions.USER_UPDATE,
            user_id=current_user.id,
            entity_type="user",
            entity_id=user.id,
            details={"changes": changes},
        )

    return user


@router.put("/{user_id}/password", response_model=UserResponse)
def reset_user_password(
    user_id: str,
    request: PasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reset a user's password."""
    # Find user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # Validate password
    if not request.password or len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters.",
        )

    # Update password
    user.password_hash = hash_password(request.password)
    db.commit()
    db.refresh(user)

    # Log audit event
    log_audit_event(
        db=db,
        action=AuditActions.USER_PASSWORD_RESET,
        user_id=current_user.id,
        entity_type="user",
        entity_id=user.id,
        details={"username": user.username},
    )

    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a user."""
    # Prevent deleting yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account.",
        )

    # Find user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # Prevent deleting the last active user
    if user.is_active:
        active_user_count = db.query(User).filter(User.is_active == True).count()
        if active_user_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last active user.",
            )

    username = user.username

    # Delete user
    db.delete(user)
    db.commit()

    # Log audit event
    log_audit_event(
        db=db,
        action=AuditActions.USER_DELETE,
        user_id=current_user.id,
        entity_type="user",
        entity_id=user_id,
        details={"username": username},
    )
