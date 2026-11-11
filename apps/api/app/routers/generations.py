"""Generations: the main creation surface.

Flow per request:
1. Validate model + capabilities + plan gate (shared `services/stepgen`).
2. Compute deterministic credit estimate (shown to user = deducted amount).
3. ONE transaction: create Generation + Job, reserve credits, refund on ANY failure.
4. Worker picks up lease→provider→assets; failure → automatic refund.
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import session
from app.models import Asset, Generation, GenerationJob, User
from app.schemas import (AssetOut, GenerationCreate, GenerationDetail, GenerationList,
                         GenerationOut)
from app.services import credits as credit_svc
from app.services import jobs as job_svc
from app.services import stepgen
from app.services.auth import current_user

router = APIRouter(prefix="/v1/generations", tags=["generations"])


@router.post("/preview-cost", status_code=200)
async def preview_cost(body: GenerationCreate, user: User = Depends(current_user),
                       s: AsyncSession = Depends(session)):
    model = await stepgen.get_active_model(s, body.model_id)
    return {"estimated_credits": stepgen.estimate(model, body), "model_id": model.id}


@router.post("", response_model=GenerationDetail, status_code=201)
async def create_generation(body: GenerationCreate, user: User = Depends(current_user),
                            s: AsyncSession = Depends(session)):
    if body.idempotency_key:
        existing = (await s.execute(select(Generation).where(
            Generation.user_id == user.id,
            Generation.idempotency_key == body.idempotency_key))).scalar_one_or_none()
        if existing:
            return await _detail(s, existing, lazy=True)
    try:
        gen = await stepgen.create_from_body(s, user.id, body)
        await s.flush()
        await job_svc.enqueue(s, gen)
        await s.commit()
    except credit_svc.InsufficientCredits as e:
        await s.rollback()
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED,
                            {"code": "INSUFFICIENT_CREDITS", "need": e.need, "have": e.have,
                             "message": f"insufficient credits: need {e.need}, have {e.have}"})
    except HTTPException:
        await s.rollback()
        raise
    except Exception:
        await s.rollback()
        raise
    await s.refresh(gen)
    detail = await _detail(s, gen)
    return detail


async def _detail(s: AsyncSession, gen: Generation, lazy: bool = False) -> GenerationDetail:
    assets = []
    if not lazy:
        rows = (await s.execute(select(Asset).where(Asset.generation_id == gen.id,
                                                    Asset.deleted_at.is_(None))
                                .order_by(Asset.created_at))).scalars().all()
        assets = [AssetOut.model_validate(a) for a in rows]
    d = GenerationDetail.model_validate({**GenerationOut.model_validate(gen).model_dump(), "assets": assets})
    return d


@router.get("", response_model=GenerationList)
async def list_generations(status_filter: str | None = Query(None, alias="status"),
                           project_id: str | None = None, cursor: int | None = None,
                           limit: int = Query(50, le=100),
                           user: User = Depends(current_user), s: AsyncSession = Depends(session)):
    q = select(Generation).where(Generation.user_id == user.id)
    if status_filter:
        q = q.where(Generation.status == status_filter)
    if project_id:
        q = q.where(Generation.project_id == project_id)
    if cursor is not None:
        q = q.where(Generation.id < cursor)
    q = q.order_by(Generation.created_at.desc()).limit(limit)
    rows = (await s.execute(q)).scalars().all()
    return GenerationList(items=[GenerationOut.model_validate(g) for g in rows],
                          next=rows[-1].id if len(rows) == limit else None)


@router.get("/{generation_id}", response_model=GenerationDetail)
async def get_generation(generation_id: str, user: User = Depends(current_user),
                         s: AsyncSession = Depends(session)):
    gen = (await s.execute(select(Generation).where(Generation.id == generation_id,
                                                    Generation.user_id == user.id))).scalar_one_or_none()
    if not gen:
        raise HTTPException(404, "generation not found")
    return await _detail(s, gen)


@router.post("/{generation_id}/cancel", response_model=GenerationOut)
async def cancel_generation(generation_id: str, user: User = Depends(current_user),
                            s: AsyncSession = Depends(session)):
    gen = (await s.execute(select(Generation).where(Generation.id == generation_id,
                                                    Generation.user_id == user.id))).scalar_one_or_none()
    if not gen:
        raise HTTPException(404, "generation not found")
    if gen.status in ("queued", "running"):
        job = (await s.execute(select(GenerationJob).where(GenerationJob.generation_id == gen.id))).scalar_one_or_none()
        if job and job.provider_job_ref:
            try:
                provider = await job_svc.get_provider_for_model(s, gen.model_id)
                await provider.cancel(job.provider_job_ref)
            except Exception:
                pass
        gen.status = "canceled"
        gen.completed_at = dt.datetime.now(dt.timezone.utc)
        if gen.actual_credits > 0:
            await credit_svc.refund(s, user.id, gen.actual_credits, "cancellation refund", gen.id)
            gen.actual_credits = 0
        if job:
            job.status = "canceled"
        await s.commit()
    await s.refresh(gen)
    return GenerationOut.model_validate(gen)


@router.post("/{generation_id}/reroll", response_model=GenerationDetail, status_code=201)
async def reroll(generation_id: str, user: User = Depends(current_user),
                 s: AsyncSession = Depends(session)):
    src = (await s.execute(select(Generation).where(Generation.id == generation_id,
                                                    Generation.user_id == user.id))).scalar_one_or_none()
    if not src:
        raise HTTPException(404, "generation not found")
    body = GenerationCreate.model_validate({
        **{k: v for k, v in (src.params or {}).items() if k not in ("first_frame_asset_id",)},
        "media_type": src.media_type, "task": src.task, "model_id": src.model_id,
        "prompt": src.prompt, "negative_prompt": src.negative_prompt,
        "project_id": src.project_id, "idempotency_key": None,
    })
    return await create_generation(body, user, s)
