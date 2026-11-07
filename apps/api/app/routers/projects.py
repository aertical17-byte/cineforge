"""Projects CRUD."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import session
from app.models import Asset, Generation, Project
from app.schemas import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.auth import current_user
from app.models import User

router = APIRouter(prefix="/v1/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
async def list_projects(user: User = Depends(current_user), s: AsyncSession = Depends(session)):
    res = await s.execute(
        select(Project).where(Project.user_id == user.id, Project.deleted_at.is_(None))
        .order_by(Project.updated_at.desc())
    )
    return res.scalars().all()


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(body: ProjectCreate, user: User = Depends(current_user),
                         s: AsyncSession = Depends(session)):
    p = Project(user_id=user.id, name=body.name, description=body.description)
    s.add(p)
    await s.commit()
    await s.refresh(p)
    return p


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str, user: User = Depends(current_user),
                      s: AsyncSession = Depends(session)):
    p = (await s.execute(select(Project).where(Project.id == project_id,
                                               Project.user_id == user.id,
                                               Project.deleted_at.is_(None)))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "project not found")
    return p


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(project_id: str, body: ProjectUpdate, user: User = Depends(current_user),
                         s: AsyncSession = Depends(session)):
    p = (await s.execute(select(Project).where(Project.id == project_id, Project.user_id == user.id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "project not found")
    for field_name in ("name", "description", "is_archived"):
        val = getattr(body, field_name)
        if val is not None:
            setattr(p, field_name, val)
    await s.commit()
    await s.refresh(p)
    return p


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, user: User = Depends(current_user),
                         s: AsyncSession = Depends(session)):
    p = (await s.execute(select(Project).where(Project.id == project_id, Project.user_id == user.id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "project not found")
    p.deleted_at = dt.datetime.now(dt.timezone.utc)
    await s.commit()
    return None
