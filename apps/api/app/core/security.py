"""Password hashing + JWT helpers. Zero raw secrets stored."""
from __future__ import annotations

import datetime as dt
import hmac
import hashlib
from typing import Any, Dict, Optional

import bcrypt
import jwt

from app.core.config import get_settings

_settings = get_settings()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: str, extra: Optional[Dict[str, Any]] = None) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload: Dict[str, Any] = {
        "sub": user_id,
        "iat": now,
        "exp": now + dt.timedelta(seconds=_settings.jwt_ttl_seconds),
        "iss": "cineforge",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, _settings.jwt_secret, algorithm=_settings.jwt_algorithm)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, _settings.jwt_secret, algorithms=[_settings.jwt_algorithm], issuer="cineforge")
    except jwt.PyJWTError:
        return None


def new_local_signing_key() -> (str, str):  # type: ignore[valid-type]
    """Pair (prefix, digest) for API keys: store digest only."""
    import secrets

    raw = "cf_" + secrets.token_urlsafe(24)
    return raw[:12], _digest(raw)


def _digest(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def check_api_key(raw: str, digest: str) -> bool:
    return hmac.compare_digest(_digest(raw), digest)


def sign_url_token(key: str, ttl: int | None = None) -> str:
    """HMAC-signed URL token for local storage mode (mirrors S3 presigned URLs)."""
    import time

    ttl = ttl or _settings.signed_url_ttl
    exp = int(time.time()) + ttl
    sig = hmac.new(_settings.jwt_secret.encode(), f"{key}:{exp}".encode(), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"
