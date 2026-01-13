"""Authentication utilities for the REST API."""
import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import get_db
from app.database.models import User


# JWT configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

# Security scheme for Swagger docs
security = HTTPBearer()


# Pydantic models
class LoginRequest(BaseModel):
    """Login request body."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response body."""
    token: str
    token_type: str = "bearer"
    expires_at: datetime


class UserResponse(BaseModel):
    """User response body."""
    id: str
    username: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


# Password utilities
def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-SHA256.

    Returns a string in format: salt$hash (both base64 encoded)
    """
    salt = os.urandom(32)
    hash_bytes = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        iterations=100000
    )
    salt_b64 = base64.b64encode(salt).decode('utf-8')
    hash_b64 = base64.b64encode(hash_bytes).decode('utf-8')
    return f"{salt_b64}${hash_b64}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        salt_b64, hash_b64 = hashed_password.split('$')
        salt = base64.b64decode(salt_b64)
        stored_hash = base64.b64decode(hash_b64)

        computed_hash = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt,
            iterations=100000
        )
        return secrets.compare_digest(stored_hash, computed_hash)
    except (ValueError, TypeError):
        return False


# JWT utilities using HMAC
def _base64url_encode(data: bytes) -> str:
    """Base64url encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def _base64url_decode(data: str) -> bytes:
    """Base64url decode with padding restoration."""
    padding = 4 - len(data) % 4
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data)


def create_access_token(user_id: str, username: str) -> tuple[str, datetime]:
    """Create a JWT access token using HMAC-SHA256.

    Args:
        user_id: The user's ID
        username: The user's username

    Returns:
        Tuple of (token string, expiration datetime)
    """
    expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # JWT header
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _base64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))

    # JWT payload
    payload = {
        "sub": user_id,
        "username": username,
        "exp": int(expires_at.timestamp()),
    }
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))

    # Signature
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        settings.secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    signature_b64 = _base64url_encode(signature)

    token = f"{header_b64}.{payload_b64}.{signature_b64}"
    return token, expires_at


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT token.

    Args:
        token: The JWT token string

    Returns:
        The decoded payload

    Raises:
        HTTPException: If the token is invalid or expired
    """
    try:
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid token format")

        header_b64, payload_b64, signature_b64 = parts

        # Verify signature
        message = f"{header_b64}.{payload_b64}"
        expected_signature = hmac.new(
            settings.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        actual_signature = _base64url_decode(signature_b64)

        if not secrets.compare_digest(expected_signature, actual_signature):
            raise ValueError("Invalid signature")

        # Decode payload
        payload = json.loads(_base64url_decode(payload_b64))

        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            raise ValueError("Token expired")

        return payload

    except (ValueError, TypeError, json.JSONDecodeError, KeyError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# User authentication
def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate a user by username and password.

    Args:
        db: Database session
        username: The username to authenticate
        password: The password to verify

    Returns:
        The User object if authentication succeeds, None otherwise
    """
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


# FastAPI dependencies
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency to get the current authenticated user.

    Args:
        credentials: The HTTP Bearer credentials
        db: Database session

    Returns:
        The authenticated User object

    Raises:
        HTTPException: If authentication fails
    """
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
        )
    return user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Get current user if authenticated, None otherwise.

    This dependency does not require authentication - it returns None
    if no valid token is provided.

    Args:
        credentials: Optional HTTP Bearer credentials
        db: Database session

    Returns:
        The User object if authenticated, None otherwise
    """
    if not credentials:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            return None
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            return None
        return user
    except HTTPException:
        return None
