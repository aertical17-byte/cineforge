"""Generations: the main creation surface.

Flow per request:
1. Validate model + capabilities + plan gate.
2. Compute deterministic credit estimate (shown to user = deducted amount).
3. ONE transaction: create Generation + Job, reserve credits, refund on ANY failure.
4. Worker picks up lease→provider→assetsware; failure → automatic refund.
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import session
from app.models import (AIModel, Asset, Generation, GenerationJob, Plan, Subscription,
                        User)
from app.schemas import (AssetOut, GenerationCreate, GenerationDetail, GenerationList,
                         GenerationOut)
from app.services import credits as credit_svc
from app.services import jobs as job_svc
from app.services.auth import current_user
from app.services.prompt_engine import credit_cost, registries
from app.services.registry import caps

router = APIRouter(prefix="/v1/generations", tags=["generations"])


def _estimate(model: AIModel, body: GenerationCreate) -> int:
    return credit_cost(model, body.media_type, body.duration_s or 0, body.batch_size, body.resolution)


def _validate(model: AIModel, body: GenerationCreate) -> None:
    c = caps(model)
    tasks = model.tasks or []
    if f"{'image' if body.media_type == 'image' else 'video'}" not in tasks and body.task != "upscale":
        raise HTTPException(422, f"model {model.id} does not support this media type")
    if body.aspect_ratio not in (c.get("aspect_ratios") or []):
        raise HTTPException(422, f"aspect ratio {body.aspect_ratio} unsupported by {model.id}")
    if body.media_type == "video":
        maxdur = int(c.get("max_duration_s") or 0)
        if body.duration_s and maxdur and body.duration_s > maxdur:
            raise HTTPException(422, f"max duration {maxdur}s for {model.id}")
    if body.camera_move and body.camera_move not in {r["id"] for r in registries()["camera_moves"]}:
        raise HTTPException(422, "unknown camera move")
    if body.camera_move and not c.get("supports_camera_control") and body.task == "img2video":
        # still allowed: it degrades to prompt text; nothing fake is claimed
        pass
    fs = body.film_setup
    if fs:
        table = {
            "genre": "genres", "era": "eras", "tempo": "tempo", "camera_body": "camera_bodies",
            "lens": "lenses", "aperture": "apertures", "palette": "palettes",
            "lighting": "lighting_presets", "speed_ramp": "speed_ramps", "moveset_style": "moveset_styles",
        }
        for key, group in table.items():
            v = getattr(fs, key)
            if v and v not in {r["id"] for r in registries()[group]}:
                raise HTTPException(422, f"unknown {key} '{v}'")


async def _plan_gate(user: User, model: AIModel, s: AsyncSession) -> None:
    sub = (await s.execute(select(Subscription).where(Subscription.user_id == user.id,
                                                      Subscription.status.in_(["active", "past_due"])))).scalar_one_or_none()
    plan = sub.plan_code if sub else "free"
    order = ["free", "creator", "studio", "enterprise"]
    if order.index(model.min_plan) > order.index(plan):
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED,
                            f"{model.id} requires plan '{model.min_plan}'; current plan '{plan}'")


@router.post("/preview-cost", status_code=200)
async def preview_cost(body: GenerationCreate, user: User = Depends(current_user),
                       s: AsyncSession = Depends(session)):
    model = (await s.execute(select(AIModel).where(AIModel.id == body.model_id, AIModel.is_active.is_(True)))).scalar_one_or_none()
    if not model:
        raise HTTPException(404, "model not found")
    return {"estimated_credits": _estimate(model, body), "model_id": model.id}


@router.post("", response_model=GenerationDetail, status_code=201)
async def create_generation(body: GenerationCreate, user: User = Depends(current_user),
                            s: AsyncSession = Depends(session)):
    model = (await s.execute(select(AIModel).where(AIModel.id == body.model_id, AIModel.is_active.is_(True)))).scalar_one_or_none()
    if not model:
        raise HTTPException(404, "model not found")
    if body.idempotency_key:
        existing = (await s.execute(select(Generation).where(
            Generation.user_id == user.id,
            Generation.idempotency_key == body.idempotency_key))).scalar_one_or_none()
        if existing:
            return await _detail(s, existing, lazy=True)
    _validate(model, body)
    await _plan_gate(user, model, s)
    estimate = _estimate(model, body)

    params = body.model_dump(exclude={"idempotency_key"}, exclude_none=True)
    params["reference_asset_ids"] = body.reference_asset_ids
    if body.task == "img2video" and body.reference_asset_ids:
        params["first_frame_asset_id"] = body.reference_asset_ids[0]
    gen = Generation(user_id=user.id, project_id=body.project_id, media_type=body.media_type,
                     task=body.task, model_id=model.id, prompt=body.prompt,
                     negative_prompt=body.negative_prompt, params=params,
                     estimated_credits=estimate, batch_size=body.batch_size,
                     idempotency_key=body.idempotency_key)
    try:
        s.add(gen)
        await s.flush()
        await credit_svc.reserve_for_generation(
            s, user.id, gen.id, estimate,
            f"{body.task} · {model.display_name}",
        )
        await job_svc.enqueue(s, gen)
        gen.actual_credits = estimate
        await s.commit()
    except credit_svc.InsufficientCredits as e:
        await s.rollback()
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED,
                            f"insufficient credits: need {e.need}, have {e.have}")
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
