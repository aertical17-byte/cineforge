"""Admin: plans, credit grants, user management, verification status."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import session
from app.core.config import get_settings
from app.models import (AIModel, AIProvider, AuditLog, Plan, User)
from app.schemas import AdminCreditGrant, AdminUserOut
from app.services import credits as credit_svc
from app.services.auth import admin_user

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserOut])
async def users(user: User = Depends(admin_user), s: AsyncSession = Depends(session)):
    rows = (await s.execute(select(User).order_by(User.created_at.desc()).limit(200))).scalars().all()
    return rows


@router.post("/credits/grant", status_code=201)
async def grant_credits(body: AdminCreditGrant, admin: User = Depends(admin_user),
                        s: AsyncSession = Depends(session)):
    target = await s.get(User, body.user_id)
    if not target:
        return {"error": "user not found"}
    await credit_svc.grant(s, body.user_id, body.amount, body.kind, "admin",
                           f"grant by admin {admin.id}", body.days_valid)
    s.add(AuditLog(actor_user_id=admin.id, action="admin.credit_grant",
                   entity="user", entity_id=body.user_id,
                   detail={"amount": body.amount, "kind": body.kind}))
    await s.commit()
    return {"ok": True}


class PlanUpsert(BaseModel):
    code: str
    name: str
    monthly_price_cents: int = 0
    yearly_price_cents: int = 0
    monthly_credits: int = 0
    max_concurrency: int = 1
    features: list[str] = []


@router.post("/plans", status_code=201)
async def upsert_plan(body: PlanUpsert, admin: User = Depends(admin_user),
                      s: AsyncSession = Depends(session)):
    plan = (await s.execute(select(Plan).where(Plan.code == body.code))).scalar_one_or_none()
    if plan:
        for k, v in body.model_dump().items():
            setattr(plan, k, v)
    else:
        s.add(Plan(**body.model_dump()))
    s.add(AuditLog(actor_user_id=admin.id, action="admin.plan_upsert", entity="plan", entity_id=body.code))
    await s.commit()
    return {"ok": True}


@router.get("/providers/status")
async def provider_status(admin: User = Depends(admin_user), s: AsyncSession = Depends(session)):
    S = get_settings()
    rows = (await s.execute(select(AIProvider))).scalars().all()
    return [{"id": p.id, "docs_url": p.docs_url, "requires_key": p.requires_key,
             "configured": bool((p.id == "replicate" and S.replicate_api_token) or
                                (p.id == "fal" and S.fal_key) or p.id == "mock")} for p in rows]


@router.get("/models")
async def models(admin: User = Depends(admin_user), s: AsyncSession = Depends(session)):
    rows = (await s.execute(select(AIModel))).scalars().all()
    return rows
