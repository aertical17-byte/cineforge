"""FastAPI application factory.

Security posture: strict CORS, security headers middleware, per-route auth, DB-backed
rate limiting hook, audit logging on mutating requests, no provider keys in responses.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text

from app.core.config import get_settings
from app.core.db import Base, SessionFactory, engine, session
from app.models import AuditLog  # noqa: F401 (model import registers tables)
from app.routers import (admin, assets, auth, billing, credits, elements, generations,
                         pipelines,
                         projects, users)
from app.services.seed import seed

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # bootstrap; Alembic owns upgrades (see CI)
    if s.seed_registry_on_startup:
        async with SessionFactory() as session_:
            await seed(session_)
    yield


app = FastAPI(
    title="CineForge AI API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api-docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.method in ("POST", "PATCH", "DELETE"):
        try:
            actor = getattr(getattr(request.state, "user", None), "id", None)
            if resp.status_code < 500:
                async with SessionFactory() as s_:
                    s_.add(AuditLog(actor_user_id=actor, action=f"http.{request.method}",
                                    entity=str(request.url.path), ip=request.client.host if request.client else ""))
                    await s_.commit()
        except Exception:  # never let audit logging break responses
            log.exception("audit write failed")
    return resp


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(assets.router)
app.include_router(assets.router_files)
app.include_router(generations.router)
app.include_router(pipelines.router)
app.include_router(credits.router)
app.include_router(billing.router)
app.include_router(elements.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    async with SessionFactory() as s:
        await s.execute(text("select 1"))
    return {"ok": True, "service": "cineforge-api"}
