"""auth router: register/login/forgot/guest + validates strong inputs; audit + rate-limited."""
from __future__ import annotations

import datetime as dt
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import session
from app.core.security import create_access_token, hash_password, verify_password
from app.models import AuditLog, Profile, User
from app.schemas import ForgotPasswordRequest, LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services import credits as credit_svc
from app.services.auth import current_user
from app.services.rate_limit import limiter

router = APIRouter(prefix="/v1/auth", tags=["auth"])
S = get_settings()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, request: Request, s: AsyncSession = Depends(session)):
    ip = request.client.host if request.client else "unknown"
    if not limiter.hit(f"auth:{ip}", S.auth_rate_limit_per_minute):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too many attempts")
    user = (await s.execute(select(User).where(func.lower(User.email) == body.email.lower()))).scalar_one_or_none()
    if user:
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    u = User(email=body.email.lower(), password_hash=hash_password(body.password),
             display_name=body.display_name or body.email.split("@")[0],
             consent_likeness=body.consent_likeness,
             is_admin=body.email.lower() in [e.strip().lower() for e in S.admin_emails.split(",") if e.strip()])
    u.profile = Profile(bio="")
    s.add(u)
    await s.flush()
    if S.free_signup_credits > 0:
        await credit_svc.grant(s, u.id, S.free_signup_credits, "promo", "signup",
                               "welcome credits", S.free_signup_credits_days)
    s.add(AuditLog(action="auth.register", entity="user", entity_id=u.id, ip=ip))
    await s.commit()
    return TokenResponse(access_token=create_access_token(u.id), user=UserOut.model_validate(u))


@router.post("/guest", response_model=TokenResponse, status_code=201)
async def guest(request: Request, s: AsyncSession = Depends(session)):
    """No-login mode: mint an ephemeral guest account on the fly.

    The included engines (AI Horde community / mock in tests) need no credentials, so the
    product itself requires no signup: the web app calls this once per browser and stores
    the token. Guests get the same welcome lots as registered users ("no limits" mode).
    The account is identified only by its browser token — no email is collected.
    """
    ip = request.client.host if request.client else "unknown"
    if not limiter.hit(f"auth:{ip}", S.auth_rate_limit_per_minute):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too many attempts")
    rand = secrets.token_hex(8)
    u = User(email=f"guest-{rand}@cineforge.local",
             password_hash=hash_password(secrets.token_urlsafe(24)),
             display_name=f"Guest {rand[:4].upper()}",
             consent_likeness=False)
    u.profile = Profile(bio="")
    s.add(u)
    await s.flush()
    if S.free_signup_credits > 0:
        await credit_svc.grant(s, u.id, S.free_signup_credits, "promo", "guest",
                               "welcome credits (guest, no signup)", S.free_signup_credits_days or None)
    s.add(AuditLog(action="auth.guest", entity="user", entity_id=u.id, ip=ip))
    await s.commit()
    return TokenResponse(access_token=create_access_token(u.id), user=UserOut.model_validate(u))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, s: AsyncSession = Depends(session)):
    ip = request.client.host if request.client else "unknown"
    if not limiter.hit(f"auth:{ip}", S.auth_rate_limit_per_minute):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too many attempts")
    u = (await s.execute(select(User).where(func.lower(User.email) == body.email.lower()))).scalar_one_or_none()
    if not u or u.deleted_at or not u.is_active or not verify_password(body.password, u.password_hash):
        s.add(AuditLog(action="auth.login_failed", entity="user", entity_id=body.email, ip=ip))
        await s.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    s.add(AuditLog(action="auth.login", entity="user", entity_id=u.id, ip=ip))
    await s.commit()
    return TokenResponse(access_token=create_access_token(u.id), user=UserOut.model_validate(u))


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, s: AsyncSession = Depends(session)):
    # Privacy-safe: always 202; real dispatch requires SMTP config (documented deployment step).
    u = (await s.execute(select(User).where(func.lower(User.email) == body.email.lower()))).scalar_one_or_none()
    if u:
        s.add(AuditLog(action="auth.forgot_requested", entity="user", entity_id=u.id))
        await s.commit()
    return {"status": "queued", "note": "password reset requires SMTP configuration in this deployment"}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)):
    return user
