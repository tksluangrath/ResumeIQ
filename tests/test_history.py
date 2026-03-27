from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import Scan, User
from api.security import hash_password


async def _create_user(db: AsyncSession, email: str = "user@example.com") -> User:
    user = User(email=email, hashed_password=hash_password("password123"))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _add_scan(db: AsyncSession, user: User, endpoint: str = "match", score: float = 0.75) -> Scan:
    scan = Scan(
        user_id=user.id,
        endpoint=endpoint,
        overall_score=score,
        job_snippet="Senior Python Engineer at Acme Corp",
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return scan


async def _token_for(client: AsyncClient, email: str = "user@example.com") -> str:
    resp = await client.post("/auth/login", json={"email": email, "password": "password123"})
    return resp.json()["access_token"]


class TestListHistory:
    async def test_empty_history_returns_empty_list(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        token = await _token_for(async_client)
        resp = await async_client.get("/history", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["has_next"] is False

    async def test_returns_own_scans_only(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user_a = await _create_user(db_session, email="a@example.com")
        user_b = await _create_user(db_session, email="b@example.com")
        await _add_scan(db_session, user_a)
        await _add_scan(db_session, user_b)

        token = await _token_for(async_client, email="a@example.com")
        resp = await async_client.get("/history", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["endpoint"] == "match"

    async def test_pagination_has_next_true(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session)
        for i in range(5):
            await _add_scan(db_session, user, score=float(i) / 10)

        token = await _token_for(async_client)
        resp = await async_client.get("/history?page=1&page_size=3", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 3
        assert body["total"] == 5
        assert body["has_next"] is True

    async def test_pagination_last_page_has_next_false(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session)
        for i in range(3):
            await _add_scan(db_session, user, score=float(i) / 10)

        token = await _token_for(async_client)
        resp = await async_client.get("/history?page=1&page_size=5", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["has_next"] is False

    async def test_list_history_requires_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/history")
        assert resp.status_code == 401


class TestGetScan:
    async def test_get_own_scan_returns_200(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session)
        scan = await _add_scan(db_session, user)

        token = await _token_for(async_client)
        resp = await async_client.get(f"/history/{scan.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(scan.id)
        assert body["endpoint"] == "match"
        assert body["overall_score"] == pytest.approx(0.75)

    async def test_get_other_users_scan_returns_404(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """IDOR prevention: another user's scan must look like 404, not 403."""
        user_a = await _create_user(db_session, email="a@example.com")
        user_b = await _create_user(db_session, email="b@example.com")
        scan_b = await _add_scan(db_session, user_b)

        token_a = await _token_for(async_client, email="a@example.com")
        resp = await async_client.get(
            f"/history/{scan_b.id}", headers={"Authorization": f"Bearer {token_a}"}
        )
        assert resp.status_code == 404

    async def test_get_nonexistent_scan_returns_404(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session)
        token = await _token_for(async_client)
        resp = await async_client.get(
            f"/history/{uuid.uuid4()}", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 404

    async def test_get_scan_requires_auth(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session)
        scan = await _add_scan(db_session, user)
        resp = await async_client.get(f"/history/{scan.id}")
        assert resp.status_code == 401
