"""
Adversarial stress tests for Track 2: Stripe billing.
Goal: scan limit enforcement, plan state machine, webhook edge cases, Stripe error handling.
100 tests — requires PostgreSQL (resumeiq_test).
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import stripe as stripe_lib
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.db import User
from api.routers.billing import PLAN_SCAN_LIMITS, _price_to_plan
from api.security import hash_password
from config import Settings


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _create_user(
    db: AsyncSession,
    email: str = "billing@example.com",
    plan: str = "free",
    scan_count: int = 0,
    stripe_customer_id: str | None = None,
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password("TestPass123!"),
        plan=plan,
        scan_count=scan_count,
        stripe_customer_id=stripe_customer_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _token_for(client: AsyncClient, email: str = "billing@example.com") -> str:
    resp = await client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _mock_checkout_url(url: str = "https://checkout.stripe.com/pay/test") -> tuple:
    mock_customer = MagicMock(id="cus_test123")
    mock_session = MagicMock(url=url)
    return mock_customer, mock_session


def _make_event(event_type: str, data: dict) -> dict:
    return {"type": event_type, "data": {"object": data}}


# ── Section 1: PLAN_SCAN_LIMITS contract tests ────────────────────────────────

class TestPlanScanLimits:
    def test_free_plan_limit_is_5(self) -> None:
        assert PLAN_SCAN_LIMITS["free"] == 5

    def test_starter_plan_limit_is_25(self) -> None:
        assert PLAN_SCAN_LIMITS["starter"] == 25

    def test_pro_plan_has_no_limit(self) -> None:
        assert PLAN_SCAN_LIMITS["pro"] is None

    def test_all_paid_plans_present(self) -> None:
        assert "starter" in PLAN_SCAN_LIMITS
        assert "pro" in PLAN_SCAN_LIMITS

    def test_free_plan_present(self) -> None:
        assert "free" in PLAN_SCAN_LIMITS

    def test_unknown_plan_not_in_limits(self) -> None:
        assert "enterprise" not in PLAN_SCAN_LIMITS

    def test_price_to_plan_starter(self) -> None:
        settings = MagicMock()
        settings.STRIPE_PRICE_STARTER = "price_starter_abc"
        settings.STRIPE_PRICE_PRO = "price_pro_abc"
        assert _price_to_plan("price_starter_abc", settings) == "starter"

    def test_price_to_plan_pro(self) -> None:
        settings = MagicMock()
        settings.STRIPE_PRICE_STARTER = "price_starter_abc"
        settings.STRIPE_PRICE_PRO = "price_pro_abc"
        assert _price_to_plan("price_pro_abc", settings) == "pro"

    def test_price_to_plan_unknown_returns_none(self) -> None:
        settings = MagicMock()
        settings.STRIPE_PRICE_STARTER = "price_starter_abc"
        settings.STRIPE_PRICE_PRO = "price_pro_abc"
        assert _price_to_plan("price_unknown_xyz", settings) is None

    def test_price_to_plan_empty_string_returns_none(self) -> None:
        settings = MagicMock()
        settings.STRIPE_PRICE_STARTER = "price_starter_abc"
        settings.STRIPE_PRICE_PRO = "price_pro_abc"
        assert _price_to_plan("", settings) is None


# ── Section 2: Billing status endpoint ───────────────────────────────────────

class TestBillingStatus:
    async def test_free_plan_status(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        tok = await _token_for(async_client)
        resp = await async_client.get("/billing/status", headers={"Authorization": f"Bearer {tok}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["plan"] == "free"
        assert body["scan_limit"] == 5

    async def test_starter_plan_limit_is_25(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session, plan="starter")
        tok = await _token_for(async_client)
        resp = await async_client.get("/billing/status", headers={"Authorization": f"Bearer {tok}"})
        assert resp.json()["scan_limit"] == 25

    async def test_pro_plan_limit_is_null(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session, plan="pro")
        tok = await _token_for(async_client)
        resp = await async_client.get("/billing/status", headers={"Authorization": f"Bearer {tok}"})
        assert resp.json()["scan_limit"] is None

    async def test_scan_count_reflects_db(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session, scan_count=3)
        tok = await _token_for(async_client)
        resp = await async_client.get("/billing/status", headers={"Authorization": f"Bearer {tok}"})
        assert resp.json()["scan_count"] == 3

    async def test_status_unauthenticated_401(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/billing/status")
        assert resp.status_code == 401

    async def test_status_with_stripe_customer_id(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session, stripe_customer_id="cus_known123")
        tok = await _token_for(async_client)
        resp = await async_client.get("/billing/status", headers={"Authorization": f"Bearer {tok}"})
        assert resp.json()["stripe_customer_id"] == "cus_known123"

    async def test_status_without_stripe_customer_id_is_null(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        tok = await _token_for(async_client)
        resp = await async_client.get("/billing/status", headers={"Authorization": f"Bearer {tok}"})
        assert resp.json()["stripe_customer_id"] is None

    async def test_status_has_all_required_fields(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        tok = await _token_for(async_client)
        resp = await async_client.get("/billing/status", headers={"Authorization": f"Bearer {tok}"})
        body = resp.json()
        assert {"plan", "scan_count", "scan_limit", "stripe_customer_id"}.issubset(body.keys())


# ── Section 3: Checkout endpoint stress ───────────────────────────────────────

class TestCheckoutStress:
    async def test_checkout_starter_200(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        tok = await _token_for(async_client)
        mock_cus, mock_sess = _mock_checkout_url("https://checkout.stripe.com/pay/starter_test")
        with (
            patch("api.routers.billing.stripe.Customer.create", return_value=mock_cus),
            patch("api.routers.billing.stripe.checkout.Session.create", return_value=mock_sess),
        ):
            resp = await async_client.post(
                "/billing/checkout",
                json={"plan": "starter", "success_url": "http://app/success", "cancel_url": "http://app/cancel"},
                headers={"Authorization": f"Bearer {tok}"},
            )
        assert resp.status_code == 200
        assert resp.json()["checkout_url"] == "https://checkout.stripe.com/pay/starter_test"

    async def test_checkout_pro_200(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        tok = await _token_for(async_client)
        mock_cus, mock_sess = _mock_checkout_url("https://checkout.stripe.com/pay/pro_test")
        with (
            patch("api.routers.billing.stripe.Customer.create", return_value=mock_cus),
            patch("api.routers.billing.stripe.checkout.Session.create", return_value=mock_sess),
        ):
            resp = await async_client.post(
                "/billing/checkout",
                json={"plan": "pro", "success_url": "http://app/success", "cancel_url": "http://app/cancel"},
                headers={"Authorization": f"Bearer {tok}"},
            )
        assert resp.status_code == 200

    async def test_checkout_free_plan_rejected_422(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        tok = await _token_for(async_client)
        resp = await async_client.post(
            "/billing/checkout",
            json={"plan": "free", "success_url": "http://app/success", "cancel_url": "http://app/cancel"},
            headers={"Authorization": f"Bearer {tok}"},
        )
        assert resp.status_code == 422

    async def test_checkout_enterprise_rejected_422(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        tok = await _token_for(async_client)
        resp = await async_client.post(
            "/billing/checkout",
            json={"plan": "enterprise", "success_url": "http://app/success", "cancel_url": "http://app/cancel"},
            headers={"Authorization": f"Bearer {tok}"},
        )
        assert resp.status_code == 422

    async def test_checkout_unauthenticated_401(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/billing/checkout",
            json={"plan": "starter", "success_url": "http://app/s", "cancel_url": "http://app/c"},
        )
        assert resp.status_code == 401

    async def test_checkout_missing_plan_field_422(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        tok = await _token_for(async_client)
        resp = await async_client.post(
            "/billing/checkout",
            json={"success_url": "http://app/s", "cancel_url": "http://app/c"},
            headers={"Authorization": f"Bearer {tok}"},
        )
        assert resp.status_code == 422

    async def test_checkout_missing_success_url_422(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        tok = await _token_for(async_client)
        resp = await async_client.post(
            "/billing/checkout",
            json={"plan": "starter", "cancel_url": "http://app/c"},
            headers={"Authorization": f"Bearer {tok}"},
        )
        assert resp.status_code == 422

    async def test_checkout_creates_stripe_customer_when_missing(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session)
        assert user.stripe_customer_id is None
        tok = await _token_for(async_client)
        mock_cus, mock_sess = _mock_checkout_url()
        with (
            patch("api.routers.billing.stripe.Customer.create", return_value=mock_cus) as mock_create,
            patch("api.routers.billing.stripe.checkout.Session.create", return_value=mock_sess),
        ):
            await async_client.post(
                "/billing/checkout",
                json={"plan": "starter", "success_url": "http://s", "cancel_url": "http://c"},
                headers={"Authorization": f"Bearer {tok}"},
            )
            mock_create.assert_called_once()

    async def test_checkout_reuses_existing_stripe_customer_id(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session, stripe_customer_id="cus_existing")
        tok = await _token_for(async_client)
        _, mock_sess = _mock_checkout_url()
        with (
            patch("api.routers.billing.stripe.Customer.create") as mock_create,
            patch("api.routers.billing.stripe.checkout.Session.create", return_value=mock_sess),
        ):
            await async_client.post(
                "/billing/checkout",
                json={"plan": "pro", "success_url": "http://s", "cancel_url": "http://c"},
                headers={"Authorization": f"Bearer {tok}"},
            )
            mock_create.assert_not_called()

    async def test_checkout_saves_stripe_customer_id_to_db(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session)
        tok = await _token_for(async_client)
        mock_cus = MagicMock(id="cus_newlysaved")
        mock_sess = MagicMock(url="https://checkout.stripe.com/pay/x")
        with (
            patch("api.routers.billing.stripe.Customer.create", return_value=mock_cus),
            patch("api.routers.billing.stripe.checkout.Session.create", return_value=mock_sess),
        ):
            resp = await async_client.post(
                "/billing/checkout",
                json={"plan": "starter", "success_url": "http://s", "cancel_url": "http://c"},
                headers={"Authorization": f"Bearer {tok}"},
            )
        assert resp.status_code == 200
        await db_session.refresh(user)
        assert user.stripe_customer_id == "cus_newlysaved"

    async def test_checkout_response_has_checkout_url(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        tok = await _token_for(async_client)
        _, mock_sess = _mock_checkout_url("https://checkout.stripe.com/test")
        with (
            patch("api.routers.billing.stripe.Customer.create", return_value=MagicMock(id="cus_x")),
            patch("api.routers.billing.stripe.checkout.Session.create", return_value=mock_sess),
        ):
            resp = await async_client.post(
                "/billing/checkout",
                json={"plan": "starter", "success_url": "http://s", "cancel_url": "http://c"},
                headers={"Authorization": f"Bearer {tok}"},
            )
        assert "checkout_url" in resp.json()

    async def test_checkout_empty_body_422(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        tok = await _token_for(async_client)
        resp = await async_client.post(
            "/billing/checkout", json={}, headers={"Authorization": f"Bearer {tok}"}
        )
        assert resp.status_code == 422


# ── Section 4: Customer portal stress ────────────────────────────────────────

class TestPortalStress:
    async def test_portal_requires_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/billing/portal")
        assert resp.status_code == 401

    async def test_portal_without_customer_400(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        tok = await _token_for(async_client)
        resp = await async_client.get("/billing/portal", headers={"Authorization": f"Bearer {tok}"})
        assert resp.status_code == 400

    async def test_portal_with_customer_returns_url(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session, stripe_customer_id="cus_portal_test")
        tok = await _token_for(async_client)
        mock_portal = MagicMock(url="https://billing.stripe.com/session/test")
        with patch("api.routers.billing.stripe.billing_portal.Session.create", return_value=mock_portal):
            resp = await async_client.get("/billing/portal", headers={"Authorization": f"Bearer {tok}"})
        assert resp.status_code == 200
        assert resp.json()["portal_url"] == "https://billing.stripe.com/session/test"

    async def test_portal_400_detail_message(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        tok = await _token_for(async_client)
        resp = await async_client.get("/billing/portal", headers={"Authorization": f"Bearer {tok}"})
        assert "detail" in resp.json()
        assert "checkout" in resp.json()["detail"].lower()

    async def test_portal_response_has_portal_url_key(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session, stripe_customer_id="cus_p2")
        tok = await _token_for(async_client)
        with patch(
            "api.routers.billing.stripe.billing_portal.Session.create",
            return_value=MagicMock(url="https://billing.stripe.com/x"),
        ):
            resp = await async_client.get("/billing/portal", headers={"Authorization": f"Bearer {tok}"})
        assert "portal_url" in resp.json()


# ── Section 5: Webhook stress ─────────────────────────────────────────────────

class TestWebhookStress:
    async def test_bad_signature_returns_400(self, async_client: AsyncClient) -> None:
        with patch(
            "api.routers.billing.stripe.Webhook.construct_event",
            side_effect=stripe_lib.error.SignatureVerificationError("bad", "t=1"),
        ):
            resp = await async_client.post(
                "/billing/webhook", content=b"{}", headers={"stripe-signature": "bad"}
            )
        assert resp.status_code == 400

    async def test_checkout_completed_upgrades_plan(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session, stripe_customer_id="cus_wh_stress_1")
        assert user.plan == "free"
        event = _make_event("checkout.session.completed", {
            "mode": "subscription",
            "customer": "cus_wh_stress_1",
            "subscription": "sub_test_1",
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
                "/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=ok"}
            )
        assert resp.status_code == 200
        await db_session.refresh(user)
        assert user.plan == "starter"

    async def test_subscription_updated_upgrades_plan(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session, stripe_customer_id="cus_wh_stress_2", plan="starter")
        event = _make_event("customer.subscription.updated", {
            "customer": "cus_wh_stress_2",
            "items": {"data": [{"price": {"id": "price_pro_test"}}]},
        })
        with (
            patch("api.routers.billing.stripe.Webhook.construct_event", return_value=event),
            patch("api.routers.billing._price_to_plan", return_value="pro"),
        ):
            resp = await async_client.post(
                "/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=ok"}
            )
        assert resp.status_code == 200
        await db_session.refresh(user)
        assert user.plan == "pro"

    async def test_subscription_deleted_resets_to_free(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session, stripe_customer_id="cus_wh_stress_3", plan="pro")
        event = _make_event("customer.subscription.deleted", {"customer": "cus_wh_stress_3"})
        with patch("api.routers.billing.stripe.Webhook.construct_event", return_value=event):
            resp = await async_client.post(
                "/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=ok"}
            )
        assert resp.status_code == 200
        await db_session.refresh(user)
        assert user.plan == "free"

    async def test_unknown_event_type_returns_200_ok(self, async_client: AsyncClient) -> None:
        event = _make_event("payment_intent.created", {"id": "pi_test"})
        with patch("api.routers.billing.stripe.Webhook.construct_event", return_value=event):
            resp = await async_client.post(
                "/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=ok"}
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_checkout_completed_non_subscription_mode_ignored(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session, stripe_customer_id="cus_wh_stress_4")
        event = _make_event("checkout.session.completed", {
            "mode": "payment",  # not subscription
            "customer": "cus_wh_stress_4",
        })
        with patch("api.routers.billing.stripe.Webhook.construct_event", return_value=event):
            resp = await async_client.post(
                "/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=ok"}
            )
        assert resp.status_code == 200
        await db_session.refresh(user)
        assert user.plan == "free"  # unchanged

    async def test_webhook_for_unknown_customer_does_not_crash(
        self, async_client: AsyncClient
    ) -> None:
        event = _make_event("customer.subscription.deleted", {"customer": "cus_nonexistent_xyz"})
        with patch("api.routers.billing.stripe.Webhook.construct_event", return_value=event):
            resp = await async_client.post(
                "/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=ok"}
            )
        assert resp.status_code == 200

    async def test_webhook_missing_signature_header(self, async_client: AsyncClient) -> None:
        with patch(
            "api.routers.billing.stripe.Webhook.construct_event",
            side_effect=stripe_lib.error.SignatureVerificationError("no sig", ""),
        ):
            resp = await async_client.post("/billing/webhook", content=b"{}")
        assert resp.status_code == 400

    async def test_webhook_replay_same_event_is_idempotent(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Sending the same subscription.deleted event twice must not crash."""
        user = await _create_user(db_session, stripe_customer_id="cus_replay", plan="starter")
        event = _make_event("customer.subscription.deleted", {"customer": "cus_replay"})
        for _ in range(2):
            with patch("api.routers.billing.stripe.Webhook.construct_event", return_value=event):
                resp = await async_client.post(
                    "/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=ok"}
                )
            assert resp.status_code == 200
        await db_session.refresh(user)
        assert user.plan == "free"


# ── Section 6: Scan limit enforcement ────────────────────────────────────────

class TestScanLimitEnforcement:
    async def test_free_user_at_scan_limit_blocked(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """A free user with scan_count == limit should be blocked from matching."""
        from api.dependencies import check_and_increment_scan
        user = await _create_user(db_session, scan_count=5, plan="free")
        with pytest.raises(Exception):
            await check_and_increment_scan(user, db_session)

    async def test_free_user_below_limit_allowed(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """A free user at scan_count=4 (< 5) must NOT raise."""
        from api.dependencies import check_and_increment_scan
        user = await _create_user(db_session, scan_count=4, plan="free")
        # Should not raise
        await check_and_increment_scan(user, db_session)
        await db_session.refresh(user)
        assert user.scan_count == 5

    async def test_pro_user_never_blocked(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Pro users have None limit → never blocked."""
        from api.dependencies import check_and_increment_scan
        user = await _create_user(db_session, scan_count=9999, plan="pro")
        # Should not raise — pro has no limit
        await check_and_increment_scan(user, db_session)
        await db_session.refresh(user)
        assert user.scan_count == 10000

    async def test_starter_user_at_limit_blocked(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from api.dependencies import check_and_increment_scan
        user = await _create_user(db_session, scan_count=25, plan="starter")
        with pytest.raises(Exception):
            await check_and_increment_scan(user, db_session)

    async def test_scan_count_increments_on_allowed_call(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from api.dependencies import check_and_increment_scan
        user = await _create_user(db_session, scan_count=0, plan="free")
        await check_and_increment_scan(user, db_session)
        await db_session.refresh(user)
        assert user.scan_count == 1

    async def test_scan_count_does_not_increment_when_blocked(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from api.dependencies import check_and_increment_scan
        user = await _create_user(db_session, scan_count=5, plan="free")
        try:
            await check_and_increment_scan(user, db_session)
        except Exception:
            pass
        await db_session.refresh(user)
        assert user.scan_count == 5  # unchanged


# ── Section 7: Plan state machine integrity ───────────────────────────────────

class TestPlanStateMachine:
    async def test_free_to_starter_via_webhook(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session, stripe_customer_id="cus_state_1")
        assert user.plan == "free"
        event = _make_event("customer.subscription.updated", {
            "customer": "cus_state_1",
            "items": {"data": [{"price": {"id": "price_starter"}}]},
        })
        with (
            patch("api.routers.billing.stripe.Webhook.construct_event", return_value=event),
            patch("api.routers.billing._price_to_plan", return_value="starter"),
        ):
            await async_client.post(
                "/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=ok"}
            )
        await db_session.refresh(user)
        assert user.plan == "starter"

    async def test_starter_to_pro_via_webhook(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session, stripe_customer_id="cus_state_2", plan="starter")
        event = _make_event("customer.subscription.updated", {
            "customer": "cus_state_2",
            "items": {"data": [{"price": {"id": "price_pro"}}]},
        })
        with (
            patch("api.routers.billing.stripe.Webhook.construct_event", return_value=event),
            patch("api.routers.billing._price_to_plan", return_value="pro"),
        ):
            await async_client.post(
                "/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=ok"}
            )
        await db_session.refresh(user)
        assert user.plan == "pro"

    async def test_pro_to_free_via_cancellation(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session, stripe_customer_id="cus_state_3", plan="pro")
        event = _make_event("customer.subscription.deleted", {"customer": "cus_state_3"})
        with patch("api.routers.billing.stripe.Webhook.construct_event", return_value=event):
            await async_client.post(
                "/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=ok"}
            )
        await db_session.refresh(user)
        assert user.plan == "free"

    async def test_unknown_price_id_does_not_change_plan(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session, stripe_customer_id="cus_state_4", plan="starter")
        event = _make_event("customer.subscription.updated", {
            "customer": "cus_state_4",
            "items": {"data": [{"price": {"id": "price_unknown"}}]},
        })
        with (
            patch("api.routers.billing.stripe.Webhook.construct_event", return_value=event),
            patch("api.routers.billing._price_to_plan", return_value=None),
        ):
            resp = await async_client.post(
                "/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=ok"}
            )
        assert resp.status_code == 200
        await db_session.refresh(user)
        assert user.plan == "starter"  # unchanged

    async def test_billing_status_updates_after_plan_change(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session, stripe_customer_id="cus_state_5")
        tok = await _token_for(async_client)

        # Confirm free plan
        resp = await async_client.get("/billing/status", headers={"Authorization": f"Bearer {tok}"})
        assert resp.json()["plan"] == "free"
        assert resp.json()["scan_limit"] == 5

        # Upgrade via webhook
        event = _make_event("customer.subscription.updated", {
            "customer": "cus_state_5",
            "items": {"data": [{"price": {"id": "price_pro"}}]},
        })
        with (
            patch("api.routers.billing.stripe.Webhook.construct_event", return_value=event),
            patch("api.routers.billing._price_to_plan", return_value="pro"),
        ):
            await async_client.post(
                "/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=ok"}
            )

        # Confirm pro plan in status
        resp2 = await async_client.get("/billing/status", headers={"Authorization": f"Bearer {tok}"})
        assert resp2.json()["plan"] == "pro"
        assert resp2.json()["scan_limit"] is None
