"""Test fixtures — **the only environment where the mock provider is allowed** (AI_MOCK_MODE=1)."""
from __future__ import annotations

import asyncio
import os
import pathlib

os.environ["AI_MOCK_MODE"] = "1"
os.environ["ENVIRONMENT"] = "test"
os.environ["SEED_REGISTRY_ON_STARTUP"] = "0"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/test-api.db"
os.environ["ADMIN_EMAILS"] = "admin@cineforge.test"

for suffix in ("", "-wal", "-shm", "-journal"):
    p = pathlib.Path("./data/test-api.db" + suffix)
    if p.exists():
        p.unlink()
pathlib.Path("./data/storage").mkdir(parents=True, exist_ok=True)

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.core.config import get_settings  # noqa: E402
get_settings.cache_clear()  # freeze settings for the test env

from app.core.db import Base, session as dep_session  # noqa: E402

TEST_DB_URL = os.environ["DATABASE_URL"]
TestEngine = create_async_engine(TEST_DB_URL)
SessionFactory = async_sessionmaker(TestEngine, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def _schema():
    async def run():
        async with TestEngine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(run())
    yield


@pytest.fixture
async def client():
    async def _session():
        async with SessionFactory() as s:
            yield s

    from app.main import app
    from app.services import jobs as jobsmod

    app.dependency_overrides[dep_session] = _session
    orig_sf = jobsmod.SessionFactory
    jobsmod.SessionFactory = SessionFactory  # worker-side session support in-process

    from app.services.seed import seed

    async with SessionFactory() as s:
        await seed(s)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test-api"
    ) as c:
        yield app, c

    jobsmod.SessionFactory = orig_sf
    app.dependency_overrides.clear()


async def _token(client: AsyncClient, email: str) -> str:
    r = await client.post("/v1/auth/register", json={
        "email": email, "password": "Str0ngPassword",
    })
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def auth_header(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}"}
