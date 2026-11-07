"""Authn/authz: JWT bearer + API-key authentication, permission checks."""
from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import check_api_key, decode_token
from app.core.db import session
from app.models import APIKey, User

bearer_scheme = HTTPBearer(auto_error=False)


async def current_user(request: Request, s: AsyncSession = Depends(session),
                       creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> User:
    token = creds.credentials if creds else None
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    claims = decode_token(token)
    if not claims:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired token")
    user_id = claims.get("sub")
    user = (await s.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "account unavailable")
    request.state.user = user
    return user


async def optional_user(request: Request, s: AsyncSession = Depends(session),
                        creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> Optional[User]:
    if creds:
        claims = decode_token(creds.credentials)
        if claims:
            user = await s.get(User, claims.get("sub"))
            if user and user.is_active:
                return user
    return None


async def admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin only")
    return user


async def auth_from_api_key(request: Request, s: AsyncSession = Depends(session)) -> User:
    raw = request.headers.get("x-api-key") or ""
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing api key")
    rows = (await s.execute(select(APIKey).where(APIKey.prefix == raw[:12]))).scalars().all()
    for row in rows:
        if row.revoked_at:
            continue
        if check_api_key(raw, row.key_digest):
            user = await s.get(User, row.user_id)
            if user and user.is_active:
                row.last_used_at = dt.datetime.now(dt.timezone.utc)
                request.state.user = user
                return user
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid api key")
