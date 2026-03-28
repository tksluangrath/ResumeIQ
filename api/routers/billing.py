from __future__ import annotations

from typing import Any

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.dependencies import get_db, require_current_user
from api.models import BillingStatusResponse, CheckoutResponse, PortalResponse
from config import Settings, get_settings

router = APIRouter(prefix="/billing", tags=["billing"])

PLAN_SCAN_LIMITS: dict[str, int | None] = {
    "free": 3,
    "starter": 20,
    "pro": None,
}


def _price_to_plan(price_id: str, settings: Settings) -> str | None:
    if price_id == settings.STRIPE_PRICE_STARTER:
        return "starter"
    if price_id == settings.STRIPE_PRICE_PRO:
        return "pro"
    return None


class CheckoutRequest(BaseModel):
    plan: str
    success_url: str
    cancel_url: str


@router.get("/status", response_model=BillingStatusResponse)
async def billing_status(
    user: Any = Depends(require_current_user),
    settings: Settings = Depends(get_settings),
) -> BillingStatusResponse:
    return BillingStatusResponse(
        plan=user.plan,
        scan_count=user.scan_count,
        scan_limit=PLAN_SCAN_LIMITS.get(user.plan),
        stripe_customer_id=user.stripe_customer_id,
    )


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    user: Any = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CheckoutResponse:
    if body.plan not in ("starter", "pro"):
        raise HTTPException(status_code=422, detail="plan must be 'starter' or 'pro'")

    price_id = settings.STRIPE_PRICE_STARTER if body.plan == "starter" else settings.STRIPE_PRICE_PRO
    stripe.api_key = settings.STRIPE_SECRET_KEY

    if user.stripe_customer_id is None:
        customer = stripe.Customer.create(email=user.email)
        user.stripe_customer_id = customer.id
        await db.commit()

    session = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=body.success_url,
        cancel_url=body.cancel_url,
    )
    return CheckoutResponse(checkout_url=session.url)


@router.get("/portal", response_model=PortalResponse)
async def customer_portal(
    user: Any = Depends(require_current_user),
    settings: Settings = Depends(get_settings),
) -> PortalResponse:
    if user.stripe_customer_id is None:
        raise HTTPException(status_code=400, detail="No billing account found. Complete a checkout first.")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    portal = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:8501",
    )
    return PortalResponse(portal_url=portal.url)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    from api.db import User

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    event_type: str = event["type"]
    data: dict = event["data"]["object"]

    if event_type == "checkout.session.completed":
        if data.get("mode") != "subscription":
            return {"status": "ignored"}
        customer_id: str = data["customer"]
        # Determine plan from the subscription's price
        subscription_id = data.get("subscription")
        if subscription_id:
            sub = stripe.Subscription.retrieve(subscription_id)
            price_id = sub["items"]["data"][0]["price"]["id"]
            plan = _price_to_plan(price_id, settings)
            if plan:
                result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
                db_user = result.scalar_one_or_none()
                if db_user:
                    db_user.plan = plan
                    await db.commit()

    elif event_type == "customer.subscription.updated":
        customer_id = data["customer"]
        price_id = data["items"]["data"][0]["price"]["id"]
        plan = _price_to_plan(price_id, settings)
        if plan:
            result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
            db_user = result.scalar_one_or_none()
            if db_user:
                db_user.plan = plan
                await db.commit()

    elif event_type == "customer.subscription.deleted":
        customer_id = data["customer"]
        result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
        db_user = result.scalar_one_or_none()
        if db_user:
            db_user.plan = "free"
            await db.commit()

    return {"status": "ok"}
