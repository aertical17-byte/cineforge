"""Transactional credit ledger — the heart of the economy (docs/TECHNICAL_ARCHITECTURE.md §credits).

Invariants (enforced inside transactions; verified by tests):
1. A lot is a positive transaction with remaining>0. Spending reduces lots in strict order:
   subscription lots first, then non-subscription lots by soonest expiry.
2. Generations reserve (deduct) credits up-front in the same transaction that creates the Generation row
   (fixed credit estimate, so concurrency races cannot overspend).
3. Failed jobs refund actual credits as `refund` source while preserving the usage trail.
4. Balance never goes negative.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional, Tuple

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import CreditTransaction, Generation, UsageLog


async def balance(session: AsyncSession, user_id: str) -> int:
    res = await session.execute(
        select(func.coalesce(func.sum(CreditTransaction.amount), 0)).where(CreditTransaction.user_id == user_id)
    )
    return int(res.scalar_one())


async def summary(session: AsyncSession, user_id: str) -> dict:
    res = await session.execute(
        select(CreditTransaction)
        .where(CreditTransaction.user_id == user_id, CreditTransaction.amount > 0,
               CreditTransaction.remaining > 0)
    )
    lots = res.scalars().all()
    sub = sum(l.remaining for l in lots if l.kind == "subscription")
    others = sorted([l for l in lots if l.kind != "subscription"], key=lambda l: (l.expires_at or dt.datetime.max.replace(tzinfo=dt.timezone.utc)))
    soonest_lot = sum(l.remaining for l in others[:1])
    soonest_date = others[0].expires_at if others else None
    return {
        "balance": sum(l.remaining for l in lots),
        "subscription_lot": sub,
        "soonest_expiry_lot": soonest_lot,
        "soonest_expiry_date": soonest_date,
    }


def _spend_order_query():
    """Ordered lots: subscription first; then soonest expiry; only unexpired lots with remaining>0."""
    now = dt.datetime.now(dt.timezone.utc)
    q = (
        select(CreditTransaction)
        .where(
            CreditTransaction.amount > 0,
            CreditTransaction.remaining > 0,
        )
        .where(
            CreditTransaction.expires_at.is_(None) | (CreditTransaction.expires_at > now)
        )
        .order_by(
            case((CreditTransaction.kind == "subscription", 0), else_=1),
            case((CreditTransaction.expires_at.is_(None), dt.datetime.max.replace(tzinfo=dt.timezone.utc)), else_=CreditTransaction.expires_at),
        )
    )
    if get_settings().database_url.startswith("postgresql"):
        q = q.with_for_update(skip_locked=False)
    return q


async def grant(session: AsyncSession, user_id: str, amount: int, kind: str, source: str,
                description: str, days_valid: Optional[int] = None) -> CreditTransaction:
    """Add a positive lot (purchase / signup / promo / renewal). Committing is caller's job."""
    expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=days_valid) if days_valid else None
    lot = CreditTransaction(
        user_id=user_id, kind=kind, amount=amount, remaining=amount,
        source=source, description=description, expires_at=expires,
    )
    session.add(lot)
    await session.flush()
    session.add(UsageLog(user_id=user_id, event=source, credits_delta=amount, meta={"kind": kind, "description": description}))
    return lot


async def _spend_from_lots(session: AsyncSession, user_id: str, amount: int, description: str,
                           generation_id: str) -> int:
    res = await session.execute(_spend_order_query().where(CreditTransaction.user_id == user_id))
    lots = res.scalars().all()
    have = sum(l.remaining for l in lots)
    if have < amount:
        raise InsufficientCredits(have, amount)
    left = amount
    for lot in lots:
        if left <= 0:
            break
        take = min(lot.remaining, left)
        lot.remaining -= take
        left -= take
        session.add(CreditTransaction(
            user_id=user_id, kind=lot.kind, amount=-take, remaining=0,
            source="spend", description=description, generation_id=generation_id,
            expires_at=lot.expires_at,
        ))
    session.add(UsageLog(user_id=user_id, event="generation", credits_delta=-amount,
                         meta={"description": description, "generation_id": generation_id}))
    return amount - left if left > 0 else amount


async def reserve_for_generation(session: AsyncSession, user_id: str, generation_id: str,
                                 amount: int, description: str) -> int:
    """Called in the same transaction as the Generation insert. => same commit ⇒ refund-on-failure is honest."""
    return await _spend_from_lots(session, user_id, amount, description, generation_id)


async def refund(session: AsyncSession, user_id: str, amount: int, description: str,
                 generation_id: str) -> CreditTransaction:
    """Refund a failed generation; refunds never expire before 90 days standard lot rules (soonest-expiry protection)."""
    lot = CreditTransaction(
        user_id=user_id, kind="refund", amount=amount, remaining=amount,
        source="refund", description=description, generation_id=generation_id,
        # refunds inherit "expires" semantics of refund lots; keep 90-day cap for hygiene
        expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=90),
    )
    session.add(lot)
    await session.flush()
    session.add(UsageLog(user_id=user_id, event="refund", credits_delta=amount,
                         meta={"description": description, "generation_id": generation_id}))
    return lot


class InsufficientCredits(Exception):
    def __init__(self, have: int, need: int):
        super().__init__(f"insufficient credits: have={have} need={need}")
        self.have = have
        self.need = need
