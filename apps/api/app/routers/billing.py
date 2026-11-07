"""Billing: Stripe Checkout + webhooks when configured; transparent admin-managed fallback otherwise.

Never stores card data (Stripe token model). Prices are configured by Plan rows (admin-editable).
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import session
from app.models import AuditLog, Payment, Plan, Subscription, User
from app.schemas import CheckoutRequest
from app.services import credits as credit_svc
from app.services.auth import current_user

router = APIRouter(prefix="/v1/billing", tags=["billing"])
S = get_settings()


def _stripe():
    if not S.stripe_secret_key:
        return None
    import stripe

    stripe.api_key = S.stripe_secret_key
    return stripe


@router.post("/checkout")
async def checkout(body: CheckoutRequest, user: User = Depends(current_user),
                   s: AsyncSession = Depends(session)):
    stripe = _stripe()
    plan = (await s.execute(select(Plan).where(Plan.code == body.plan_code,
                                               Plan.is_active.is_(True)))).scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "plan not found")
    price_cents = plan.yearly_price_cents if body.interval == "year" else plan.monthly_price_cents
    if stripe is None:
        await s.commit()
        return {
            "mode": "admin_nowired", "message": ("Stripe is not configured on this deployment. "
                                                "Prices, plans and credit grants remain admin-managed; "
                                                "no payment was processed."),
            "plan": body.plan_code, "amount_cents": price_cents,
        }
    price_ids = {"month": S.stripe_price_monthly, "year": S.stripe_price_yearly}
    session_ = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"quantity": 1} for _ in [0]][0:0] or [],
        price=price_ids.get(body.interval) or None,
        customer_email=user.email,
        success_url=f"{S.cors_origin_list[0]}/settings/subscription?status=success",
        cancel_url=f"{S.cors_origin_list[0]}/settings/subscription?status=cancel",
        metadata={"user_id": user.id, "plan_code": body.plan_code, "interval": body.interval},
    )
    s.add(Payment(user_id=user.id, amount_cents=price_cents, status="pending",
                  stripe_session_id=session_.id))
    await s.commit()
    return {"mode": "stripe", "checkout_url": session_.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, s: AsyncSession = Depends(session)):
    stripe = _stripe()
    if stripe is None or not S.stripe_webhook_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "webhook not configured")
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        import stripe

        event = stripe.Webhook.construct_event(payload, sig, S.stripe_webhook_secret)
    except Exception:  # noqa: BLE001 — signature verification failure must fail closed
        raise HTTPException(400, "invalid signature")
    t = event["type"]
    if t == "checkout.session.completed":
        sess = event["data"]["object"]
        meta = sess.get("metadata") or {}
        user_id = meta.get("user_id")
        plan_code = meta.get("plan_code") or "creator"
        interval = meta.get("interval") or "month"
        payment = (await s.execute(select(Payment).where(Payment.stripe_session_id == sess["id"]))).scalar_one_or_none()
        if payment:
            payment.status = "paid"
        if user_id:
            period_end = dt.datetime.now(dt.timezone.utc) + (
                dt.timedelta(days=365) if interval == "year" else dt.timedelta(days=30))
            sub = (await s.execute(select(Subscription).where(Subscription.user_id == user_id))).scalar_one_or_none()
            if sub:
                sub.plan_code = plan_code
                sub.stripe_customer_id = sess.get("customer")
                sub.stripe_subscription_id = sess.get("subscription")
                sub.status = "active"
                sub.interval = interval
                sub.current_period_end = period_end
            else:
                sub = Subscription(user_id=user_id, plan_code=plan_code, interval=interval,
                                   current_period_end=period_end,
                                   stripe_customer_id=sess.get("customer"),
                                   stripe_subscription_id=sess.get("subscription"))
                s.add(sub)
            plan = await s.execute(select(Plan).where(Plan.code == plan_code))
            plan_row = plan.scalar_one_or_none()
            if plan_row and plan_row.monthly_credits:
                await credit_svc.grant(s, user_id, plan_row.monthly_credits, "subscription",
                                       "renewal", f"{plan_code} plan credits",
                                       (365 if interval == "year" else 30))
    elif t == "invoice.payment_failed":
        sub_id = (event["data"]["object"].get("subscription"))
        subs = (await s.execute(select(Subscription).where(Subscription.stripe_subscription_id == sub_id))).scalars().all()
        for sub in subs:
            sub.status = "past_due"
    elif t == "customer.subscription.deleted":
        sub_id = event["data"]["object"]["id"]
        subs = (await s.execute(select(Subscription).where(Subscription.stripe_subscription_id == sub_id))).scalars().all()
        for sub in subs:
            sub.status = "canceled"
            sub.canceled_at = dt.datetime.now(dt.timezone.utc)
    await s.commit()
    s.add(AuditLog(action="billing.stripe_event", entity="event", entity_id=t))
    return {"received": True}
