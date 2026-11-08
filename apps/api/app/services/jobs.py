"""Job engine: DB-backed lease queue with retries, timeouts, cancellation, refund-on-failure.

Postgres uses SKIP LOCKED claim; SQLite (CI/dev) uses atomic UPDATE claim. Same semantics.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import case, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models import AIModel, Asset, Generation, GenerationJob, Notification, UsageLog
from app.providers.base import (AIProvider, Downloaded, GenerateResult, JobState,
                                ProviderError, ProviderNotConfigured, ProviderUnsupported)
from app.providers.fal import FalProvider
from app.providers.mock import MockProvider
from app.providers.replicate import ReplicateProvider
from app.services import credits as credit_svc
from app.services import prompt_engine
from app.services.registry import caps
from app.services.storage import storage

log = logging.getLogger("jobs")

FAILED = "failed"


async def get_provider(provider_id: str) -> AIProvider:
    s = get_settings()
    if provider_id == "replicate":
        return ReplicateProvider(s.replicate_api_token)
    if provider_id == "fal":
        return FalProvider(s.fal_key)
    if provider_id == "mock":
        if s.environment != "test":
            raise ProviderNotConfigured("mock")
        return MockProvider(s.storage_local_dir)
    raise ProviderError(f"unknown provider {provider_id}")


async def enqueue(session: AsyncSession, generation: Generation, now: Optional[dt.datetime] = None):
    job = GenerationJob(generation_id=generation.id, status="queued")
    session.add(job)
    return job


async def claim_next_job(session: AsyncSession, worker_id: str = "worker-0",
                         is_postgres: bool = False) -> Optional[GenerationJob]:
    now = dt.datetime.now(dt.timezone.utc)
    if is_postgres:
        query = (
            select(GenerationJob)
            .where(GenerationJob.status.in_(["queued", "retry_wait", "running"]))
            .where(
                GenerationJob.claimed_at.is_(None)
                | (GenerationJob.claimed_at < now - dt.timedelta(seconds=600))  # lease expiry
            )
            .where(
                GenerationJob.scheduled_at.is_(None) | (GenerationJob.scheduled_at <= now)
            )
            .order_by(GenerationJob.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        row = (await session.execute(query)).scalar_one_or_none()
        if not row:
            return None
        row.claimed_by, row.claimed_at = worker_id, now
        row.status = "running"
        await session.commit()
        return row
    # dialect-neutral claim (sqlite ok): two-phase update
    res = await session.execute(
        select(GenerationJob.id).where(GenerationJob.status.in_(["queued", "retry_wait"]))
        .order_by(GenerationJob.created_at).limit(1)
    )
    jid = res.scalar_one_or_none()
    if not jid:
        return None
    res = await session.execute(
        update(GenerationJob)
        .where(GenerationJob.id == jid, GenerationJob.status.in_(["queued", "retry_wait"]))
        .values(status="running", claimed_by=worker_id, claimed_at=now)
    )
    await session.commit()
    if res.rowcount != 1:
        return None
    return await session.get(GenerationJob, jid)


async def _requeue_with_backoff(session: AsyncSession, job: GenerationJob, err: Exception):
    settings = get_settings()
    attempt = job.attempt + 1
    if attempt >= settings.job_max_attempts:
        await fail(session, job, err)
        return
    backoff = min(60 * (2 ** (attempt - 1)), 600)
    job.attempt = attempt
    job.status = "retry_wait"
    job.claimed_by, job.claimed_at = None, None
    job.scheduled_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=backoff)
    await session.flush()
    log.warning("job %s failed attempt %d: %s; retry in %ss", job.id, attempt, err, backoff)


async def fail(session: AsyncSession, job: GenerationJob, err: Exception):
    gen = await session.get(Generation, job.generation_id)
    job.status = FAILED
    job.claimed_by = None
    s = get_settings()
    if isinstance(err, ProviderNotConfigured):
        code, msg = "provider_not_configured", str(err)
    elif isinstance(err, ProviderUnsupported):
        code, msg = "provider_unsupported_feature", str(err)
    else:
        code, msg = "provider_error", str(err)
    if gen:
        gen.status = FAILED
        gen.error_code = code
        gen.error_message = msg[:380]
        gen.completed_at = dt.datetime.now(dt.timezone.utc)
        if gen.actual_credits > 0:
            await credit_svc.refund(session, gen.user_id, gen.actual_credits,
                                    f"auto-refund: {gen.error_code}", gen.id)
        session.add(UsageLog(user_id=gen.user_id, event="refund", credits_delta=gen.actual_credits,
                             meta={"generation_id": gen.id, "reason": code}))
        session.add(Notification(user_id=gen.user_id, kind="generation", level="error",
                                 title=f"Generation failed ({gen.error_code})", body=msg[:400],
                                 link=f"/create?last={gen.id}"))
    await session.flush()


async def finish(session: AsyncSession, job: GenerationJob, result: GenerateResult):
    gen = await session.get(Generation, job.generation_id)
    if not gen:
        await fail(session, job, ProviderError("generation row missing"))
        return
    job.status = "succeeded"
    job.claimed_by = None
    job.provider_job_ref = result.provider_job_ref
    gen.status = "succeeded"
    gen.completed_at = dt.datetime.now(dt.timezone.utc)
    provider = await get_provider_for_model(session, gen.model_id)
    dl: Downloaded = await provider.download(result.urls)
    urls: List[str] = []
    for data, mime in zip(dl.items[: max(1, gen.batch_size)], dl.mimes):
        kind = "image" if mime.startswith("image") else ("video" if mime.startswith("video") else
               ("audio" if mime.startswith("audio") else "image"))
        key, public_url = await storage.put(data, mime, user_id=gen.user_id)
        asset = Asset(
            user_id=gen.user_id, project_id=gen.project_id, generation_id=gen.id,
            source="generation", kind=("image" if kind != "video" else "video"),
            storage_key=key, url=public_url, mime=mime, size_bytes=len(data),
        )
        session.add(asset)
        urls.append(public_url)
    session.add(Notification(user_id=gen.user_id, kind="generation", level="success",
                             title="Generation ready",
                             body=f"{gen.task} finished with {len(urls)} asset(s).",
                             link=f"/library?gen={gen.id}"))
    session.add(UsageLog(user_id=gen.user_id, event="asset_created", credits_delta=0,
                         meta={"generation_id": gen.id, "assets": len(urls)}))
    await session.flush()


async def get_provider_for_model(session: AsyncSession, model_id: str) -> AIProvider:
    model = (await session.execute(select(AIModel).where(AIModel.id == model_id))).scalar_one_or_none()
    return await get_provider(model.provider_id if model else "mock")


async def run_job(session: AsyncSession, job: GenerationJob):
    gen = await session.get(Generation, job.generation_id)
    if not gen:
        await fail(session, job, ProviderError("generation row missing"))
        return
    settings = get_settings()
    created = gen.created_at
    if created and created.tzinfo is None:  # SQLite returns naive datetimes
        created = created.replace(tzinfo=dt.timezone.utc)
    if created and (dt.datetime.now(dt.timezone.utc) - created) > dt.timedelta(seconds=settings.job_timeout_seconds):
        await fail(session, job, ProviderError("job timeout"))
        return
    model = (await session.execute(select(AIModel).where(AIModel.id == gen.model_id))).scalar_one_or_none()
    params = gen.params or {}
    refs: List[str] = []
    for aid in params.get("reference_asset_ids", []):
        a = await session.get(Asset, aid)
        if a and a.user_id == gen.user_id:
            refs.append(await storage.public_or_signed_url(a.url, a.storage_key))
    ff = None
    if params.get("first_frame_asset_id"):
        a = await session.get(Asset, params["first_frame_asset_id"])
        if a and a.user_id == gen.user_id:
            ff = await storage.public_or_signed_url(a.url, a.storage_key)
    prompt = prompt_engine.compose_prompt(gen.prompt, params.get("film_setup"),
                                          params.get("camera_move"), params.get("emotion_strength"))
    provider = await get_provider_for_model(session, gen.model_id)
    try:
        if gen.media_type == "image":
            req = prompt_engine.build_image_request(
                model, prompt, gen.negative_prompt, params.get("aspect_ratio", "1:1"),
                params.get("resolution"), params.get("seed"), params.get("steps"), params.get("guidance"),
                int(gen.batch_size or 1), refs, params.get("reference_strength"),
                model.provider_model if model else "", model.provider_config if model else {},
            )
            result = await provider.generate_image(req)
            result.urls = result.urls[: req.batch]
        else:
            already_ran = params.get("extend")
            fragment, structured = prompt_engine.resolve_camera(caps(model), params.get("camera_move"))
            req = prompt_engine.build_video_request(
                model, prompt, gen.negative_prompt, params.get("aspect_ratio", "16:9"),
                int(params.get("duration_s", 5)), params.get("seed"), ff, refs, structured,
                model.provider_model if model else "", model.provider_config if model else {},
            )
            result = await provider.generate_video(req)
            result.kind = "video"
        await finish(session, job, result)
    except ProviderError as e:
        await _requeue_with_backoff(session, job, e)
    except asyncio.TimeoutError as e:
        await _requeue_with_backoff(session, job, ProviderError(f"timeout: {e}"))
    except Exception as e:  # noqa: BLE001 — last-resort safety net for worker continuity
        log.exception("unexpected job failure")
        await _requeue_with_backoff(session, job, e)


async def process_pending(batch: int = 8):
    is_pg = get_settings().database_url.startswith("postgresql")
    async with SessionFactory() as session:
        for _ in range(batch):
            job = await claim_next_job(session, is_postgres=is_pg)
            if not job:
                break
            try:
                await run_job(session, job)
            except Exception:  # noqa: BLE001
                await session.rollback()
                raise
        await session.commit()
