from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import User
from api.security import hash_password


# ── Shared helpers (mirrors test_history.py) ─────────────────────────────────

async def _create_user(
    db: AsyncSession,
    email: str = "billing@example.com",
    stripe_customer_id: str | None = None,
    plan: str = "free",
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password("password123"),
        plan=plan,
        stripe_customer_id=stripe_customer_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _token_for(client: AsyncClient, email: str = "billing@example.com") -> str:
    resp = await client.post("/auth/login", json={"email": email, "password": "password123"})
    return resp.json()["access_token"]


# ── TestBillingStatus ─────────────────────────────────────────────────────────

class TestBillingStatus:
    async def test_free_plan_returns_correct_limit(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        token = await _token_for(async_client)
        resp = await async_client.get("/billing/status", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["plan"] == "free"
        assert body["scan_count"] == 0
        assert body["scan_limit"] == 3
        assert body["stripe_customer_id"] is None

    async def test_pro_plan_has_no_limit(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session, plan="pro")
        token = await _token_for(async_client)
        resp = await async_client.get("/billing/status", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["scan_limit"] is None

    async def test_status_requires_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/billing/status")
        assert resp.status_code == 401


# ── TestCheckout ──────────────────────────────────────────────────────────────

class TestCheckout:
    async def test_checkout_starter_returns_url(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        token = await _token_for(async_client)

        mock_customer = MagicMock(id="cus_test123")
        mock_session = MagicMock(url="https://checkout.stripe.com/pay/test_starter")

        with (
            patch("api.routers.billing.stripe.Customer.create", return_value=mock_customer),
            patch("api.routers.billing.stripe.checkout.Session.create", return_value=mock_session),
        ):
            resp = await async_client.post(
                "/billing/checkout",
                json={"plan": "starter", "success_url": "http://localhost/success", "cancel_url": "http://localhost/cancel"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        assert resp.json()["checkout_url"] == "https://checkout.stripe.com/pay/test_starter"

    async def test_checkout_pro_returns_url(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        token = await _token_for(async_client)

        mock_customer = MagicMock(id="cus_test456")
        mock_session = MagicMock(url="https://checkout.stripe.com/pay/test_pro")

        with (
            patch("api.routers.billing.stripe.Customer.create", return_value=mock_customer),
            patch("api.routers.billing.stripe.checkout.Session.create", return_value=mock_session),
        ):
            resp = await async_client.post(
                "/billing/checkout",
                json={"plan": "pro", "success_url": "http://localhost/success", "cancel_url": "http://localhost/cancel"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        assert resp.json()["checkout_url"] == "https://checkout.stripe.com/pay/test_pro"

    async def test_checkout_creates_customer_when_none(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session)
        assert user.stripe_customer_id is None

        token = await _token_for(async_client)
        mock_customer = MagicMock(id="cus_new999")
        mock_session = MagicMock(url="https://checkout.stripe.com/pay/x")

        with (
            patch("api.routers.billing.stripe.Customer.create", return_value=mock_customer) as mock_create,
            patch("api.routers.billing.stripe.checkout.Session.create", return_value=mock_session),
        ):
            resp = await async_client.post(
                "/billing/checkout",
                json={"plan": "starter", "success_url": "http://localhost/s", "cancel_url": "http://localhost/c"},
                headers={"Authorization": f"Bearer {token}"},
            )
            mock_create.assert_called_once()

        assert resp.status_code == 200
        # Refresh from DB and check stripe_customer_id was saved
        await db_session.refresh(user)
        assert user.stripe_customer_id == "cus_new999"

    async def test_checkout_reuses_existing_customer_id(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session, stripe_customer_id="cus_existing123")
        token = await _token_for(async_client)
        mock_session = MagicMock(url="https://checkout.stripe.com/pay/x")

        with (
            patch("api.routers.billing.stripe.Customer.create") as mock_create,
            patch("api.routers.billing.stripe.checkout.Session.create", return_value=mock_session),
        ):
            resp = await async_client.post(
                "/billing/checkout",
                json={"plan": "pro", "success_url": "http://localhost/s", "cancel_url": "http://localhost/c"},
                headers={"Authorization": f"Bearer {token}"},
            )
            mock_create.assert_not_called()

        assert resp.status_code == 200

    async def test_checkout_rejects_free_plan(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        token = await _token_for(async_client)
        resp = await async_client.post(
            "/billing/checkout",
            json={"plan": "free", "success_url": "http://localhost/s", "cancel_url": "http://localhost/c"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_checkout_rejects_unknown_plan(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        token = await _token_for(async_client)
        resp = await async_client.post(
            "/billing/checkout",
            json={"plan": "enterprise", "success_url": "http://localhost/s", "cancel_url": "http://localhost/c"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_checkout_requires_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/billing/checkout",
            json={"plan": "starter", "success_url": "http://localhost/s", "cancel_url": "http://localhost/c"},
        )
        assert resp.status_code == 401


# ── TestPortal ────────────────────────────────────────────────────────────────

class TestPortal:
    async def test_portal_returns_url_when_customer_exists(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session, stripe_customer_id="cus_portal123")
        token = await _token_for(async_client)
        mock_portal = MagicMock(url="https://billing.stripe.com/session/test")

        with patch("api.routers.billing.stripe.billing_portal.Session.create", return_value=mock_portal):
            resp = await async_client.get("/billing/portal", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        assert resp.json()["portal_url"] == "https://billing.stripe.com/session/test"

    async def test_portal_400_when_no_customer(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        token = await _token_for(async_client)
        resp = await async_client.get("/billing/portal", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 400

    async def test_portal_requires_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/billing/portal")
        assert resp.status_code == 401


# ── TestWebhook ───────────────────────────────────────────────────────────────

def _make_webhook_event(event_type: str, data: dict) -> dict:
    return {"type": event_type, "data": {"object": data}}


class TestWebhook:
    async def test_webhook_checkout_completed_updates_plan(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session, stripe_customer_id="cus_wh001")
        assert user.plan == "free"

        event = _make_webhook_event("checkout.session.completed", {
            "mode": "subscription",
            "customer": "cus_wh001",
            "subscription": "sub_001",
        })
        mock_sub = MagicMock()
        mock_sub.__getitem__ = lambda self, key: {
            "items": {"data": [{"price": {"id": "price_starter_test"}}]}
        }[key]

        with (
            patch("api.routers.billing.stripe.Webhook.construct_event", return_value=event),
            patch("api.routers.billing.stripe.Subscription.retrieve", return_value=mock_sub),
            patch("api.routers.billing._price_to_plan", return_value="starter"),
        ):
            resp = await async_client.post(
                "/billing/webhook",
                content=b"{}",
                headers={"stripe-signature": "t=1,v1=test"},
            )

        assert resp.status_code == 200
        await db_session.refresh(user)
        assert user.plan == "starter"

    async def test_webhook_subscription_updated_updates_plan(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session, stripe_customer_id="cus_wh002", plan="starter")

        event = _make_webhook_event("customer.subscription.updated", {
            "customer": "cus_wh002",
            "items": {"data": [{"price": {"id": "price_pro_test"}}]},
        })

        with (
            patch("api.routers.billing.stripe.Webhook.construct_event", return_value=event),
            patch("api.routers.billing._price_to_plan", return_value="pro"),
        ):
            resp = await async_client.post(
                "/billing/webhook",
                content=b"{}",
                headers={"stripe-signature": "t=1,v1=test"},
            )

        assert resp.status_code == 200
        await db_session.refresh(user)
        assert user.plan == "pro"

    async def test_webhook_subscription_deleted_resets_to_free(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session, stripe_customer_id="cus_wh003", plan="pro")

        event = _make_webhook_event("customer.subscription.deleted", {
            "customer": "cus_wh003",
        })

        with (
            patch("api.routers.billing.stripe.Webhook.construct_event", return_value=event),
            patch("api.routers.billing.get_settings") as mock_settings,
        ):
            settings = MagicMock()
            settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
            settings.STRIPE_PRICE_STARTER = "price_starter_test"
            settings.STRIPE_PRICE_PRO = "price_pro_test"
            settings.CORS_ORIGINS = ["http://localhost:8501"]
            mock_settings.return_value = settings

            resp = await async_client.post(
                "/billing/webhook",
                content=b"{}",
                headers={"stripe-signature": "t=1,v1=test"},
            )

        assert resp.status_code == 200
        await db_session.refresh(user)
        assert user.plan == "free"

    async def test_webhook_bad_signature_returns_400(self, async_client: AsyncClient) -> None:
        import stripe as stripe_lib

        with patch(
            "api.routers.billing.stripe.Webhook.construct_event",
            side_effect=stripe_lib.error.SignatureVerificationError("bad sig", "t=1,v1=bad"),
        ):
            resp = await async_client.post(
                "/billing/webhook",
                content=b"{}",
                headers={"stripe-signature": "t=1,v1=bad"},
            )

        assert resp.status_code == 400

    async def test_webhook_unknown_event_returns_200(self, async_client: AsyncClient) -> None:
        event = _make_webhook_event("payment_intent.created", {"id": "pi_test"})

        with patch("api.routers.billing.stripe.Webhook.construct_event", return_value=event):
            resp = await async_client.post(
                "/billing/webhook",
                content=b"{}",
                headers={"stripe-signature": "t=1,v1=test"},
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
