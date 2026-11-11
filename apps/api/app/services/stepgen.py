"""Spawn one generation step — single source of truth for /v1/generations and flowboard chains.

Contract: the caller owns the transaction. This module validates, estimates, adds the row
and reserves credits (InsufficientCredits on shortfall); it never commits and never
enqueues the job, so callers compose it freely without import cycles.
"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIModel, Generation, Subscription
from app.schemas import GenerationCreate
from app.services import credits as credit_svc
from app.services.prompt_engine import credit_cost, registries
from app.services.registry import caps

PLAN_ORDER = ["free", "creator", "studio", "enterprise"]


def estimate(model: AIModel, body: GenerationCreate) -> int:
    return credit_cost(model, body.media_type, body.duration_s or 0, body.batch_size, body.resolution)


def validate(model: AIModel, body: GenerationCreate) -> None:
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


async def get_active_model(s: AsyncSession, model_id: str) -> AIModel:
    model = (await s.execute(select(AIModel).where(AIModel.id == model_id, AIModel.is_active.is_(True)))).scalar_one_or_none()
    if not model:
        raise HTTPException(404, "model not found")
    return model


async def plan_gate(s: AsyncSession, user_id: str, model: AIModel) -> None:
    sub = (await s.execute(select(Subscription).where(Subscription.user_id == user_id,
                                                      Subscription.status.in_(["active", "past_due"])))).scalar_one_or_none()
    plan = sub.plan_code if sub else "free"
    if PLAN_ORDER.index(model.min_plan) > PLAN_ORDER.index(plan):
        raise HTTPException(402, f"{model.id} requires plan '{model.min_plan}'; current plan '{plan}'")


async def create_from_body(s: AsyncSession, user_id: str, body: GenerationCreate, *,
                           pipeline_id: Optional[str] = None, step: int = 0,
                           first_frame_asset_id: Optional[str] = None) -> Generation:
    """Validate → estimate → create row → reserve credits (no commit, no enqueue)."""
    model = await get_active_model(s, body.model_id)
    validate(model, body)
    await plan_gate(s, user_id, model)
    est = estimate(model, body)

    params = body.model_dump(exclude={"idempotency_key"}, exclude_none=True)
    params["reference_asset_ids"] = body.reference_asset_ids
    if body.task == "img2video" and body.reference_asset_ids:
        params["first_frame_asset_id"] = body.reference_asset_ids[0]
    if first_frame_asset_id:
        # Chain wiring wins over whatever the payload said: the video step consumes the
        # asset produced by the previous step in this pipeline.
        params["first_frame_asset_id"] = first_frame_asset_id

    gen = Generation(user_id=user_id, project_id=body.project_id, media_type=body.media_type,
                     task=body.task, model_id=model.id, prompt=body.prompt,
                     negative_prompt=body.negative_prompt, params=params,
                     estimated_credits=est, batch_size=body.batch_size,
                     idempotency_key=body.idempotency_key,
                     pipeline_id=pipeline_id, pipeline_step=step)
    s.add(gen)
    await s.flush()
    await credit_svc.reserve_for_generation(
        s, user.id, gen.id, est,
        f"{body.task} · {model.display_name}",
    )
    gen.actual_credits = est
    return gen
