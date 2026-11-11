"""Flowboard pipelines: create ordered generation chains, watch them run, cancel them."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import session
from app.models import Pipeline, User
from app.schemas import PipelineCreate, PipelineDetail, PipelineList, PipelineOut, PipelineStepOut
from app.services import pipelines as pipeline_svc
from app.services.auth import current_user

router = APIRouter(prefix="/v1/pipelines", tags=["pipelines"])


@router.post("", response_model=PipelineDetail, status_code=201)
async def create_pipeline(body: PipelineCreate, user: User = Depends(current_user),
                          s: AsyncSession = Depends(session)):
    p = await pipeline_svc.create(s, user, body)
    await s.commit()
    await s.refresh(p)
    return PipelineDetail(steps=[PipelineStepOut.model_validate(st) for st in await pipeline_svc.steps_view(s, p)],
                          **PipelineOut.model_validate(p).model_dump())


@router.get("", response_model=PipelineList)
async def list_pipelines(limit: int = Query(50, le=100), user: User = Depends(current_user),
                         s: AsyncSession = Depends(session)):
    rows = (await s.execute(select(Pipeline).where(Pipeline.user_id == user.id)
                            .order_by(Pipeline.created_at.desc()).limit(limit))).scalars().all()
    return PipelineList(items=[PipelineOut.model_validate(p) for p in rows],
                        next=rows[-1].id if len(rows) == limit else None)


@router.get("/{pipeline_id}", response_model=PipelineDetail)
async def get_pipeline(pipeline_id: str, user: User = Depends(current_user),
                       s: AsyncSession = Depends(session)):
    p = (await s.execute(select(Pipeline).where(Pipeline.id == pipeline_id,
                                                Pipeline.user_id == user.id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "pipeline not found")
    return PipelineDetail(steps=[PipelineStepOut.model_validate(st) for st in await pipeline_svc.steps_view(s, p)],
                          **PipelineOut.model_validate(p).model_dump())


@router.post("/{pipeline_id}/cancel", response_model=PipelineOut)
async def cancel_pipeline(pipeline_id: str, user: User = Depends(current_user),
                          s: AsyncSession = Depends(session)):
    p = await pipeline_svc.cancel(s, user, pipeline_id)
    await s.commit()
    await s.refresh(p)
    return PipelineOut.model_validate(p)
