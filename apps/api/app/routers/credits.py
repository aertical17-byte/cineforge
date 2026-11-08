"""Credits, usage history, catalog & registries endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import session
from app.models import (AIModel, AIProvider, Asset, CreditTransaction, Notification,
                        Plan, PresetRow, Subscription, Template, UsageLog, User)
from app.schemas import (CreditSummary, CreditTransactionOut, PlanOut, UsageOut)
from app.services import credits as credit_svc
from app.services.auth import current_user
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import datetime as dt

router = APIRouter(prefix="/v1", tags=["credits"])


@router.get("/credits/summary", response_model=CreditSummary)
async def credits_summary(user: User = Depends(current_user), s: AsyncSession = Depends(session)):
    return CreditSummary(**await credit_svc.summary(s, user.id))


@router.get("/credits/history", response_model=list[CreditTransactionOut])
async def credits_history(limit: int = 100,
                          user: User = Depends(current_user), s: AsyncSession = Depends(session)):
    rows = (await s.execute(select(CreditTransaction).where(CreditTransaction.user_id == user.id)
                            .order_by(CreditTransaction.created_at.desc()).limit(limit))).scalars().all()
    return rows


@router.get("/plans", response_model=list[PlanOut])
async def list_plans(s: AsyncSession = Depends(session)):
    rows = (await s.execute(select(Plan).where(Plan.is_active.is_(True))
                            .order_by(Plan.monthly_price_cents))).scalars().all()
    return rows


@router.get("/my/subscription")
async def my_subscription(user: User = Depends(current_user), s: AsyncSession = Depends(session)):
    sub = (await s.execute(select(Subscription).where(Subscription.user_id == user.id)
                           .limit(1))).scalar_one_or_none()
    return sub


@router.get("/usage", response_model=list[UsageOut])
async def usage(limit: int = 100, user: User = Depends(current_user), s: AsyncSession = Depends(session)):
    rows = (await s.execute(select(UsageLog).where(UsageLog.user_id == user.id)
                            .order_by(UsageLog.created_at.desc()).limit(limit))).scalars().all()
    return rows


@router.get("/models")
async def models(user: User = Depends(current_user), s: AsyncSession = Depends(session)):
    rows = (await s.execute(select(AIModel).where(AIModel.is_active.is_(True)))).scalars().all()
    out = []
    for m in rows:
        provider = await s.get(AIProvider, m.provider_id)
        out.append({
            "id": m.id, "provider": m.provider_id, "provider_name": provider.name if provider else m.provider_id,
            "family": m.family, "display_name": m.display_name, "description": m.description,
            "tasks": m.tasks, "capabilities": m.capabilities,
            "credit_cost_base": m.credit_cost_base, "credit_cost_per_second": m.credit_cost_per_second,
            "min_plan": m.min_plan, "configured": provider is not None and not provider.requires_key or True,
        })
    return out


@router.get("/registry/{group}")
async def registry_group(group: str, s: AsyncSession = Depends(session)):
    rows = (await s.execute(select(PresetRow).where(PresetRow.group == group, PresetRow.is_active.is_(True))
                            .order_by(PresetRow.id))).scalars().all()
    return [{"id": r.id, "group": r.group, "name": r.name, **{k: v for k, v in (r.payload or {}).items() if k not in ("id", "name")}} for r in rows]


@router.get("/templates")
async def templates(s: AsyncSession = Depends(session)):
    rows = (await s.execute(select(Template).where(Template.is_public.is_(True)))).scalars().all()
    return rows


@router.get("/notifications")
async def notifications(limit: int = 30, user: User = Depends(current_user), s: AsyncSession = Depends(session)):
    rows = (await s.execute(select(Notification).where(Notification.user_id == user.id)
                            .order_by(Notification.created_at.desc()).limit(limit))).scalars().all()
    return rows


@router.post("/notifications/read")
async def mark_read(user: User = Depends(current_user), s: AsyncSession = Depends(session)):
    now = dt.datetime.now(dt.timezone.utc)
    rows = (await s.execute(select(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None)))).scalars().all()
    for n in rows:
        n.read_at = now
    await s.commit()
    return {"updated": len(rows)}


@router.get("/providers")
async def providers(s: AsyncSession = Depends(session)):
    S = get_settings()
    rows = (await s.execute(select(AIProvider))).scalars().all()
    return [{
        "id": p.id, "name": p.name, "requires_key": p.requires_key,
        "configured": p.id == "mock" if S.environment == "test" else
        (p.id == "replicate" and bool(S.replicate_api_token)) or
        (p.id == "fal" and bool(S.fal_key)),
    } for p in rows]
