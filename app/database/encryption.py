"""Password encryption utilities for database connections."""
import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import settings


def _get_fernet_key() -> bytes:
    """Derive a Fernet-compatible key from the secret_key setting.

    Fernet requires a 32-byte base64-encoded key. We derive this from
    the secret_key using SHA-256.
    """
    # Hash the secret key to get 32 bytes
    key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
    # Base64 encode for Fernet
    return base64.urlsafe_b64encode(key_bytes)


def encrypt_password(password: str) -> str:
    """Encrypt a password for storage.

    Args:
        password: Plain text password

    Returns:
        Encrypted password as base64 string
    """
    if not password:
        return ""

    fernet = Fernet(_get_fernet_key())
    encrypted = fernet.encrypt(password.encode())
    return encrypted.decode()


def decrypt_password(encrypted: str) -> str:
    """Decrypt a stored password.

    Args:
        encrypted: Encrypted password from database

    Returns:
        Plain text password
    """
    if not encrypted:
        return ""

    fernet = Fernet(_get_fernet_key())
    decrypted = fernet.decrypt(encrypted.encode())
    return decrypted.decode()
