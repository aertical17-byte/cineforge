"""Async SQLAlchemy engine/session helpers (SQLite in dev/CI, Postgres in deployment)."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine():
    settings = get_settings()
    url = make_url(settings.database_url)
    if url.drivername.startswith("sqlite") and url.database not in (None, "", ":memory:"):
        # SQLite does not create missing directories; do it ourselves so a fresh
        # checkout (or CI job) can run migrations/tests without manual setup.
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)
    return create_async_engine(settings.database_url, echo=settings.db_echo, future=True)


engine = make_engine()

SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def session() -> AsyncSession:
    async with SessionFactory() as s:
        yield s
