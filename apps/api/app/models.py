"""SQLAlchemy 2.0 models — full schema (docs/DATABASE_SCHEMA.md is the prose mirror).

Notes:
- UUID strings for cross-database portability (CI sqlite ↔ deployment Postgres).
- Money/credits as integers (minor units / credit units) — never floats.
- Soft deletes where history matters (projects, generations, assets).
"""
from __future__ import annotations

import datetime as dt
import enum
import uuid
from typing import Any, Dict, Optional

from sqlalchemy import (JSON, Boolean, DateTime, Enum, Float, ForeignKey, Index,
                        Integer, String, Text, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def uid() -> str:
    return uuid.uuid4().hex


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Tier(enum.Enum):
    free = "free"
    creator = "creator"
    studio = "studio"
    enterprise = "enterprise"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    canceled = "canceled"


# ----------------------------------------------------------------------------- users
class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    avatar_asset_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("assets.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_likeness: Mapped[bool] = mapped_column(Boolean, default=False)  # likeness-consent flag for character photos
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=now)
    deleted_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 1:1 — eager-loaded so UserOut serialization never triggers a lazy IO inside
    # FastAPI's (sync) response validation path (MissingGreenlet on async drivers).
    profile: Mapped[Optional["Profile"]] = relationship(back_populates="user", uselist=False, lazy="selectin")


class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    bio: Mapped[str] = mapped_column(String(500), default="")
    company: Mapped[str] = mapped_column(String(120), default="")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    prefs: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    user: Mapped[User] = relationship(back_populates="profile")


# ----------------------------------------------------------------------------- credits
class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    # subscription | pack | auto_refill | promo | boost
    kind: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # signed; purchases >0, spend <0, refund >0
    remaining: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # remaining on a positive lot
    source: Mapped[str] = mapped_column(String(40), default="admin")  # signup|purchase|spend|refund|admin|renewal
    description: Mapped[str] = mapped_column(String(300), default="")
    generation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("generations.id"), nullable=True)
    expires_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index("ix_credits_user_spend", "user_id", "kind", "expires_at"),
    )


class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)  # free|creator|studio|enterprise
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    monthly_price_cents: Mapped[int] = mapped_column(Integer, default=0)
    yearly_price_cents: Mapped[int] = mapped_column(Integer, default=0)
    monthly_credits: Mapped[int] = mapped_column(Integer, default=0)
    max_concurrency: Mapped[int] = mapped_column(Integer, default=1)
    unlimited_models: Mapped[list] = mapped_column(JSON, default=list)
    features: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    plan_code: Mapped[str] = mapped_column(String(24), ForeignKey("plans.code"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|past_due|canceled
    interval: Mapped[str] = mapped_column(String(10), default="month")  # month|year
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    current_period_end: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(20), default="stripe")
    kind: Mapped[str] = mapped_column(String(20), default="subscription")  # subscription|credit_pack
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="usd")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    stripe_session_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Invoice(Base):
    __tablename__ = "invoices"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    payment_id: Mapped[str] = mapped_column(String(36), ForeignKey("payments.id"))
    number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    issued_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


# ----------------------------------------------------------------------------- projects & assets
class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=now)
    deleted_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("projects.id"), nullable=True, index=True)
    generation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("generations.id"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(20), default="upload")  # upload|generation
    kind: Mapped[str] = mapped_column(String(12), nullable=False)  # image|video|audio
    storage_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(String(700), default="")
    mime: Mapped[str] = mapped_column(String(80), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    thumb_storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_liked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    deleted_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Upload(Base):
    """Registry of raw client uploads (may or may not become assets)."""
    __tablename__ = "uploads"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    asset_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("assets.id"), nullable=True)
    purpose: Mapped[str] = mapped_column(String(30), default="reference")  # reference|first_frame|last_frame|avatar
    original_name: Mapped[str] = mapped_column(String(300), default="")
    mime: Mapped[str] = mapped_column(String(80), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ----------------------------------------------------------------------------- AI catalog
class AIProvider(Base):
    __tablename__ = "ai_providers"
    id: Mapped[str] = mapped_column(String(30), primary_key=True)  # replicate|fal|mock
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    docs_url: Mapped[str] = mapped_column(String(300), default="")
    base_url: Mapped[str] = mapped_column(String(200), default="")
    requires_key: Mapped[str] = mapped_column(String(60), default="")  # settings field name, e.g. fal_key
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class AIModel(Base):
    __tablename__ = "ai_models"
    id: Mapped[str] = mapped_column(String(60), primary_key=True)  # slug, e.g. "flux-schnell"
    provider_id: Mapped[str] = mapped_column(String(30), ForeignKey("ai_providers.id"), nullable=False)
    family: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(String(300), default="")
    tasks: Mapped[list] = mapped_column(JSON, default=list)  # ["image","video","edit","upscale"]
    capabilities: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    # capabilities keys: aspect_ratios, max_duration_s, supports_seed, supports_negative_prompt,
    # supports_refs, supports_camera_control, supports_last_frame, supports_audio_native,
    # resolutions, cost_per_image, cost_per_video_second, supports_upscale
    credit_cost_base: Mapped[int] = mapped_column(Integer, default=0)
    credit_cost_per_second: Mapped[int] = mapped_column(Integer, default=0)
    min_plan: Mapped[str] = mapped_column(String(24), default="free")
    provider_model: Mapped[str] = mapped_column(String(200), default="")  # provider-specific model reference
    provider_config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ProviderRegistryStatus(Base):
    """Engineering hygiene: keeps a marker of when the catalog was verified against provider docs."""
    __tablename__ = "provider_registry_status"
    provider_id: Mapped[str] = mapped_column(String(30), ForeignKey("ai_providers.id"), primary_key=True)
    verified_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[str] = mapped_column(String(300), default="")


# ----------------------------------------------------------------------------- registries
class PresetRow(Base):
    """Generic registry table seeded from packages/shared/data/creative_registries.json.

    Registry rows are (group, id) pairs: the same short id may legitimately exist in
    two groups (e.g. \"noir\" as genre and as lighting preset), so the PK is composite.
    """
    __tablename__ = "preset_rows"
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    group: Mapped[str] = mapped_column(String(40), primary_key=True)  # camera_moves|palettes|...
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Template(Base):
    """Reusable creative starting points (film setups / product looks)."""
    __tablename__ = "templates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    slug: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    category: Mapped[str] = mapped_column(String(40), default="cinematic")
    media_type: Mapped[str] = mapped_column(String(10), default="video")  # image|video
    preview_asset_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("assets.id"), nullable=True)
    prompt: Mapped[str] = mapped_column(Text, default="")
    settings: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)  # model, camera preset, palette, etc.
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ----------------------------------------------------------------------------- characters/elements
class Element(Base):
    """Reusable 'elements': characters, locations, props (identity consistency surface)."""
    __tablename__ = "elements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # character|location|prop
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), default="")
    anchor_asset_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("assets.id"), nullable=True)
    training_status: Mapped[str] = mapped_column(String(20), default="ready")  # uploading|training|ready|failed
    training_provider_job: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    attributes: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)  # emotion slider defaults, age, etc.
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    deleted_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ElementPhoto(Base):
    __tablename__ = "element_photos"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    element_id: Mapped[str] = mapped_column(String(36), ForeignKey("elements.id"), index=True, nullable=False)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id"), nullable=False)
    checked: Mapped[bool] = mapped_column(Boolean, default=False)


# ----------------------------------------------------------------------------- generation pipeline
class Generation(Base):
    __tablename__ = "generations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("projects.id"), nullable=True, index=True)
    media_type: Mapped[str] = mapped_column(String(10), nullable=False)  # image|video
    task: Mapped[str] = mapped_column(String(30), nullable=False)  # text2img|img2img|video_ref|text2video|img2video|edit_video|upscale
    model_id: Mapped[str] = mapped_column(String(60), ForeignKey("ai_models.id"), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, default="")
    negative_prompt: Mapped[str] = mapped_column(Text, default="")
    params: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)  # aspect_ratio, duration, camera, film-setup, refs...
    estimated_credits: Mapped[int] = mapped_column(Integer, default=0)
    actual_credits: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(12), default="queued", index=True)  # JobStatus values
    error_code: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    error_message: Mapped[str] = mapped_column(String(400), default="")
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    batch_size: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=now)
    completed_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_gen_user_created", "user_id", "created_at"),
        Index("ix_gen_project", "project_id", "created_at"),
        UniqueConstraint("user_id", "idempotency_key", name="uq_gen_idem"),
    )


class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    generation_id: Mapped[str] = mapped_column(String(36), ForeignKey("generations.id"), index=True, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(12), default="queued", index=True)
    claimed_by: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    claimed_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_job_ref: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    log: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=now)


# ----------------------------------------------------------------------------- platform ops
class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(30), default="system")  # generation|billing|credits|system
    level: Mapped[str] = mapped_column(String(10), default="info")  # info|success|warning|error
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    body: Mapped[str] = mapped_column(String(500), default="")
    link: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    read_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UsageLog(Base):
    __tablename__ = "usage_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    event: Mapped[str] = mapped_column(String(40), nullable=False)  # generation|refund|purchase|admin_grant|renewal
    model_id: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    credits_delta: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    entity: Mapped[str] = mapped_column(String(60), default="")
    entity_id: Mapped[str] = mapped_column(String(80), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    detail: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class APIKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(60), default="default")
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    key_digest: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    last_used_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RateLimitRow(Base):
    """DB-backed rolling rate limiter (Redis-free default; same behaviour via copies when Redis configured)."""
    __tablename__ = "rate_limit_rows"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    scope: Mapped[str] = mapped_column(String(60), index=True, nullable=False)  # e.g. auth:{ip}
    window_start: Mapped[float] = mapped_column(Float, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0)
