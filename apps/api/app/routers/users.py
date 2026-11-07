"""Users/settings router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import session
from app.models import Profile, User
from app.schemas import UserOut
from app.services.auth import current_user

router = APIRouter(prefix="/v1/me", tags=["users"])


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)
    bio: str | None = Field(default=None, max_length=500)
    company: str | None = Field(default=None, max_length=120)
    timezone: str | None = Field(default=None, max_length=64)
    prefs: dict | None = None
    consent_likeness: bool | None = None


@router.patch("", response_model=UserOut)
async def update_me(body: ProfileUpdate, user: User = Depends(current_user),
                    s: AsyncSession = Depends(session)):
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.consent_likeness is not None and body.consent_likeness is True:
        user.consent_likeness = True  # one-way consent toggle (likeness permission)
    profile = user.profile or Profile(user_id=user.id)
    if body.bio is not None:
        profile.bio = body.bio
    if body.company is not None:
        profile.company = body.company
    if body.timezone is not None:
        profile.timezone = body.timezone
    if body.prefs is not None:
        profile.prefs = body.prefs
    user.profile = profile
    await s.commit()
    await s.refresh(user)
    return user
