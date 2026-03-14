from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from src.config import settings

# Demo user — in production replace with a DB-backed users table
_DEMO_EMAIL = "demo@testmail.com"
_DEMO_PASSWORD = "demo123"


def authenticate_user(email: str, password: str) -> str | None:
    """Return email if credentials are valid, else None.

    Uses secrets.compare_digest for constant-time comparison to avoid
    timing-based enumeration of valid emails/passwords.
    """
    email_ok = secrets.compare_digest(email.lower().encode(), _DEMO_EMAIL.encode())
    pass_ok = secrets.compare_digest(password.encode(), _DEMO_PASSWORD.encode())
    if email_ok and pass_ok:
        return email.lower()
    return None


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    """Return the subject (email) if the token is valid, else None."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload.get("sub")
    except JWTError:
        return None
