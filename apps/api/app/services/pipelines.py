"""Flowboard chains: ordered generation pipelines the worker advances step by step.

Design (honest-chain rules):
- Only step 0's generation exists at creation; each later step is spawned by the
  worker right after the previous one finishes (services/jobs.finish → advance).
- The video step consumes the previous step's first asset as its first frame.
- A step reserves its own credits when it spawns: mid-chain insolvency fails the
  chain with a clear notification instead of pretending anything worked.
"""
from __future__ import annotations

import datetime as dt
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Asset, Generation, GenerationJob, Notification, Pipeline, Project, User
from app.schemas import GenerationCreate, PipelineCreate
from app.services import credits as credit_svc
from app.services import stepgen


def _body(step: dict, project_id: Optional[str], fed_by_prev: bool) -> GenerationCreate:
    media = "image" if step["kind"] == "image" else "video"
    task = "text2img" if media == "image" else ("img2video" if fed_by_prev else "text2video")
    return GenerationCreate(
        media_type=media, task=task, model_id=step["model_id"], prompt=step["prompt"],
        negative_prompt=step.get("negative_prompt") or "", project_id=project_id,
        batch_size=step.get("batch_size") or 1,
        aspect_ratio=step.get("aspect_ratio") or ("1:1" if media == "image" else "16:9"),
        duration_s=step.get("duration_s"), camera_move=step.get("camera_move"),
    )


async def _spawn(s: AsyncSession, user_id: str, p: Pipeline, index: int,
                 first_frame_asset_id: Optional[str]) -> Generation:
    step = (p.spec or {}).get("steps", [])[index]
    body = _body(step, p.project_id, first_frame_asset_id is not None)
    gen = await stepgen.create_from_body(s, user_id, body, pipeline_id=p.id, step=index,
                                         first_frame_asset_id=first_frame_asset_id)
    s.add(GenerationJob(generation_id=gen.id, status="queued"))
    return gen


async def create(s: AsyncSession, user: User, body: PipelineCreate) -> Pipeline:
    if body.project_id:
        proj = (await s.execute(select(Project).where(Project.id == body.project_id,
                                                      Project.user_id == user.id))).scalar_one_or_none()
        if not proj:
            raise HTTPException(404, "project not found")
    p = Pipeline(user_id=user.id, project_id=body.project_id, name=body.name,
                 spec={"steps": [st.model_dump(exclude_none=True) for st in body.steps]},
                 status="running")
    s.add(p)
    await s.flush()
    try:
        await _spawn(s, user.id, p, 0, None)
    except credit_svc.InsufficientCredits as e:
        await s.rollback()
        raise HTTPException(402, {"code": "INSUFFICIENT_CREDITS", "need": e.need, "have": e.have,
                                  "message": f"insufficient credits: need {e.need}, have {e.have}"})
    except HTTPException:
        await s.rollback()
        raise
    return p


async def advance(s: AsyncSession, gen: Generation) -> None:
    """Worker hook: after a chained generation succeeds, spawn the next step / close the chain."""
    if not gen.pipeline_id:
        return
    p = await s.get(Pipeline, gen.pipeline_id)
    if not p or p.status != "running":
        return
    steps = (p.spec or {}).get("steps") or []
    nxt = gen.pipeline_step + 1
    if nxt >= len(steps):
        p.status = "succeeded"
        s.add(Notification(user_id=p.user_id, kind="pipeline", level="success",
                           title="Chain finished",
                           body=f"{p.name or 'Flowboard chain'}: all {len(steps)} step(s) ready.",
                           link=f"/flowboard?id={p.id}"))
        return
    first_asset = (await s.execute(
        select(Asset).where(Asset.generation_id == gen.id, Asset.deleted_at.is_(None))
        .order_by(Asset.created_at).limit(1))).scalar_one_or_none()
    try:
        await _spawn(s, p.user_id, p, nxt, first_asset.id if first_asset else None)
    except credit_svc.InsufficientCredits as e:
        p.status = "failed"
        p.error_message = f"chain stopped at step {nxt + 1}: insufficient credits (need {e.need}, have {e.have})"
        s.add(Notification(user_id=p.user_id, kind="pipeline", level="error",
                           title="Chain stopped",
                           body=p.error_message[:400], link=f"/flowboard?id={p.id}"))
    except HTTPException as e:
        p.status = "failed"
        detail = e.detail if isinstance(e.detail, str) else str(e.detail)
        p.error_message = f"chain stopped at step {nxt + 1}: {detail}"[:390]
        s.add(Notification(user_id=p.user_id, kind="pipeline", level="error",
                           title="Chain stopped",
                           body=p.error_message[:400], link=f"/flowboard?id={p.id}"))


async def mark_failed(s: AsyncSession, gen: Generation, message: str) -> None:
    if not gen.pipeline_id:
        return
    p = await s.get(Pipeline, gen.pipeline_id)
    if not p or p.status != "running":
        return
    p.status = "failed"
    p.error_message = f"step {gen.pipeline_step + 1} failed: {message}"[:390]


async def cancel(s: AsyncSession, user: User, pipeline_id: str) -> Pipeline:
    p = (await s.execute(select(Pipeline).where(Pipeline.id == pipeline_id,
                                                Pipeline.user_id == user.id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "pipeline not found")
    if p.status == "running":
        p.status = "canceled"
        active = (await s.execute(
            select(Generation).where(Generation.pipeline_id == p.id,
                                     Generation.status.in_(["queued", "running"]))
            .order_by(Generation.pipeline_step.desc()).limit(1))).scalar_one_or_none()
        if active:
            job = (await s.execute(select(GenerationJob).where(
                GenerationJob.generation_id == active.id))).scalar_one_or_none()
            active.status = "canceled"
            active.completed_at = dt.datetime.now(dt.timezone.utc)
            if active.actual_credits > 0:
                await credit_svc.refund(s, user.id, active.actual_credits, "chain cancellation refund", active.id)
                active.actual_credits = 0
            if job:
                job.status = "canceled"
        s.add(Notification(user_id=p.user_id, kind="pipeline", level="info",
                           title="Chain canceled",
                           body=f"{p.name or 'Flowboard chain'} stopped; finished steps stay yours.",
                           link=f"/flowboard?id={p.id}"))
    return p


async def steps_view(s: AsyncSession, p: Pipeline) -> List[dict]:
    """Assemble per-step status for the API/UI: generation ids, statuses, assets."""
    gens = {g.pipeline_step: g for g in (await s.execute(
        select(Generation).where(Generation.pipeline_id == p.id)
        .order_by(Generation.pipeline_step))).scalars().all()}
    asset_rows: dict[str, list] = {}
    gids = [g.id for g in gens.values()]
    if gids:
        rows = (await s.execute(select(Asset).where(Asset.generation_id.in_(gids),
                                                    Asset.deleted_at.is_(None))
                                .order_by(Asset.created_at))).scalars().all()
        for a in rows:
            asset_rows.setdefault(a.generation_id, []).append(a)
    steps: List[dict] = []
    for i, st in enumerate((p.spec or {}).get("steps") or []):
        g = gens.get(i)
        assets = asset_rows.get(g.id, []) if g else []
        steps.append({
            "index": i,
            "kind": st.get("kind") or ("image" if i == 0 else "video"),
            "prompt": st.get("prompt") or "",
            "model_id": st.get("model_id") or "",
            "task": g.task if g else ("text2img" if st.get("kind") == "image" else "pending"),
            "status": g.status if g else "pending",
            "generation_id": g.id if g else None,
            "error_message": (g.error_message or "") if g else "",
            "assets": [a for a in assets],
        })
    return steps
