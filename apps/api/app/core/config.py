"""Runtime configuration. All secrets come from env; never commit real keys."""
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "CineForge AI API"
    environment: str = "development"  # development | test | production
    debug: bool = False

    # --- database
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    db_echo: bool = False

    # --- auth
    jwt_secret: str = Field(default="dev-only-secret-change-me")
    jwt_algorithm: str = "HS256"
    jwt_ttl_seconds: int = 60 * 60 * 24 * 14
    password_min_length: int = 10

    # --- http
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    api_rate_limit_per_minute: int = 120
    auth_rate_limit_per_minute: int = 20

    # --- storage: "local" or "s3"
    storage_backend: str = "local"
    storage_local_dir: str = "data/storage"
    s3_bucket: str = "cineforge"
    s3_region: str = ""
    s3_endpoint_url: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    signed_url_ttl: int = 3600

    # --- ai providers
    AI_MOCK_MODE: bool = False  # ONLY tests/CI may set this; production paths refuse to fake results
    replicate_api_token: Optional[str] = None
    fal_key: Optional[str] = None
    openai_api_key: Optional[str] = None  # reserved future adapter

    # --- billing (Stripe optional)
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_price_monthly: Optional[str] = None
    stripe_price_yearly: Optional[str] = None

    # --- redis (optional cache/limiter)
    redis_url: Optional[str] = None

    # --- bootstrap
    seed_registry_on_startup: bool = True
    worker_concurrency: int = 4
    job_timeout_seconds: int = 20 * 60
    job_max_attempts: int = 3
    free_signup_credits: int = 200
    free_signup_credits_days: int = 90
    admin_emails: str = "admin@cineforge.test"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
