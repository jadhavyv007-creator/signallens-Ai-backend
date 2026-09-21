"""
Cryptographic security utilities for SignalLens AI.
Implements:
- Constant-time timing-safe comparison (prevent timing attacks)
- Bcrypt password hashing
- JWT access and refresh token creation and verification
- Hashed refresh token verification for token rotation and breach detection
"""

import hmac
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import jwt, JWTError
import bcrypt
from api.config.env import env

ALGORITHM = "HS256"


def timing_safe_compare(a: str, b: str) -> bool:
    """
    Compares two strings in constant time to prevent timing attacks.
    Equivalent to crypto.timingSafeEqual in Node.js.
    """
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a bcrypt hash."""
    pwd_bytes = plain_password.encode("utf-8")[:72]
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)


def hash_token(token: str) -> str:
    """SHA-256 digest of token for indexing / quick lookup in DB."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creates a short-lived JWT access token (default: 15 minutes)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=env.JWT_ACCESS_EXPIRES_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access", "jti": uuid.uuid4().hex})
    return jwt.encode(to_encode, env.JWT_ACCESS_SECRET, algorithm=ALGORITHM)


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creates a long-lived JWT refresh token (default: 7 days)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=env.JWT_REFRESH_EXPIRES_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh", "jti": uuid.uuid4().hex})
    return jwt.encode(to_encode, env.JWT_REFRESH_SECRET, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT access token."""
    payload = jwt.decode(token, env.JWT_ACCESS_SECRET, algorithms=[ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")
    return payload


def decode_refresh_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT refresh token."""
    payload = jwt.decode(token, env.JWT_REFRESH_SECRET, algorithms=[ALGORITHM])
    if payload.get("type") != "refresh":
        raise JWTError("Invalid token type")
    return payload
