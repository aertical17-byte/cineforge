"""Pydantic schemas — keep strict validation at the border (security-first)."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# ---------------------------------------------------------------- auth
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=200)
    display_name: str = Field(default="", max_length=80)
    consent_likeness: bool = False

    @field_validator("password")
    @classmethod
    def strong(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("password needs at least one digit")
        if not any(c.isupper() for c in v):
            raise ValueError("password needs at least one uppercase letter")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


# ---------------------------------------------------------------- users
class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    bio: str = ""
    company: str = ""
    timezone: str = "UTC"
    prefs: Dict[str, Any] = {}


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    display_name: str
    is_admin: bool
    consent_likeness: bool
    created_at: dt.datetime
    profile: Optional[ProfileOut] = None


# ---------------------------------------------------------------- projects
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    is_archived: Optional[bool] = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str
    is_archived: bool
    created_at: dt.datetime
    updated_at: dt.datetime


# ---------------------------------------------------------------- assets
class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    source: str
    kind: str
    url: str
    width: Optional[int] = None
    height: Optional[int] = None
    duration_ms: Optional[int] = None
    project_id: Optional[str] = None
    generation_id: Optional[str] = None
    is_liked: bool
    created_at: dt.datetime


class AssetList(BaseModel):
    items: List[AssetOut]
    next: Optional[str] = None


# ---------------------------------------------------------------- generation
class FilmSetup(BaseModel):
    genre: Optional[str] = None
    era: Optional[str] = None
    tempo: Optional[str] = None
    camera_body: Optional[str] = None
    lens: Optional[str] = None
    aperture: Optional[str] = None
    palette: Optional[str] = None
    lighting: Optional[str] = None
    custom_lighting: Optional[Dict[str, str]] = None
    speed_ramp: Optional[str] = None
    moveset_style: Optional[str] = None


class GenerationCreate(BaseModel):
    media_type: Literal["image", "video"]
    task: Literal["text2img", "img2img", "text2video", "img2video", "video_ref", "edit_video", "extend_video", "upscale"]
    model_id: str = Field(min_length=2, max_length=60)
    prompt: str = Field(min_length=1, max_length=4000)
    negative_prompt: str = Field(default="", max_length=2000)
    project_id: Optional[str] = None
    batch_size: int = Field(default=1, ge=1, le=4)
    idempotency_key: Optional[str] = Field(default=None, max_length=100)
    aspect_ratio: str = Field(default="1:1", max_length=12)
    resolution: Optional[str] = None
    seed: Optional[int] = Field(default=None, ge=0, le=2**32 - 1)
    steps: Optional[int] = Field(default=None, ge=1, le=64)
    guidance: Optional[float] = Field(default=None, ge=0, le=15)
    duration_s: Optional[int] = Field(default=None, ge=1, le=30)
    reference_asset_ids: List[str] = Field(default_factory=list, max_length=50)
    element_ids: List[str] = Field(default_factory=list, max_length=5)
    camera_move: Optional[str] = None
    film_setup: Optional[FilmSetup] = None
    emotion_strength: Optional[float] = Field(default=None, ge=0, le=1)
    reference_strength: Optional[float] = Field(default=None, ge=0, le=1)


class GenerationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    media_type: str
    task: str
    model_id: str
    prompt: str
    params: Dict[str, Any]
    status: str
    estimated_credits: int
    actual_credits: int
    error_code: Optional[str] = None
    error_message: str
    batch_size: int
    created_at: dt.datetime
    completed_at: Optional[dt.datetime] = None


class GenerationList(BaseModel):
    items: List[GenerationOut]
    next: Optional[str] = None


class GenerationDetail(GenerationOut):
    assets: List[AssetOut] = []


# ---------------------------------------------------------------- credits
class CreditSummary(BaseModel):
    balance: int
    subscription_lot: int
    soonest_expiry_lot: int
    soonest_expiry_date: Optional[dt.datetime] = None


class CreditTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    kind: str
    amount: int
    source: str
    description: str
    expires_at: Optional[dt.datetime] = None
    created_at: dt.datetime


class UsageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    event: str
    model_id: Optional[str] = None
    credits_delta: int
    meta: Dict[str, Any] = {}
    created_at: dt.datetime


# ---------------------------------------------------------------- subscription
class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    name: str
    monthly_price_cents: int
    yearly_price_cents: int
    monthly_credits: int
    max_concurrency: int
    unlimited_models: List[str] = []
    features: List[str] = []


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    plan_code: str
    status: str
    interval: str
    current_period_end: Optional[dt.datetime] = None


class CheckoutRequest(BaseModel):
    interval: Literal["month", "year"] = "month"
    plan_code: str = "creator"


# ---------------------------------------------------------------- elements
class ElementCreate(BaseModel):
    type: Literal["character", "location", "prop"]
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=1000)
    attributes: Dict[str, Any] = {}


class ElementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    type: str
    name: str
    description: str
    training_status: str
    attributes: Dict[str, Any]
    created_at: dt.datetime


class ElementTrainingRequest(BaseModel):
    photo_asset_ids: List[str] = Field(min_length=20, max_length=80)


# ---------------------------------------------------------------- admin
class AdminUserOut(UserOut):
    is_active: bool


class AdminCreditGrant(BaseModel):
    user_id: str
    amount: int = Field(ge=1, le=100000)
    kind: str = "promo"
    days_valid: int = Field(default=30, ge=1, le=365)


TokenResponse.model_rebuild()
