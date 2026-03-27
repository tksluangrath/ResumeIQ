from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, email: str) -> str:
    """Return a signed JWT. sub = user UUID str, email included for quick display."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
    payload: dict[str, str | int] = {
        "sub": user_id,
        "email": email,
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, str | int]:
    """Decode and validate a JWT. Raises ValueError on any failure.

    Callers translate ValueError to HTTP 401.
    """
    settings = get_settings()
    try:
        payload: dict[str, str | int] = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc
    if "sub" not in payload:
        raise ValueError("Token missing sub claim")
    return payload
