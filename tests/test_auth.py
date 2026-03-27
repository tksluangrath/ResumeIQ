from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str = "user@example.com", password: str = "password123") -> dict:
    resp = await client.post("/auth/register", json={"email": email, "password": password})
    return resp


async def _login(client: AsyncClient, email: str = "user@example.com", password: str = "password123") -> dict:
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    return resp


class TestRegister:
    async def test_register_returns_201_with_token(self, async_client: AsyncClient) -> None:
        resp = await _register(async_client)
        assert resp.status_code == 201
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    async def test_register_duplicate_email_returns_409(self, async_client: AsyncClient) -> None:
        await _register(async_client)
        resp = await _register(async_client)
        assert resp.status_code == 409

    async def test_register_weak_password_returns_422(self, async_client: AsyncClient) -> None:
        resp = await _register(async_client, password="short")
        assert resp.status_code == 422

    async def test_register_invalid_email_returns_422(self, async_client: AsyncClient) -> None:
        resp = await _register(async_client, email="not-an-email")
        assert resp.status_code == 422

    async def test_register_normalises_email_to_lowercase(self, async_client: AsyncClient) -> None:
        resp = await _register(async_client, email="User@Example.COM")
        assert resp.status_code == 201
        # Registering the same address in lowercase should collide
        resp2 = await _register(async_client, email="user@example.com")
        assert resp2.status_code == 409


class TestLogin:
    async def test_login_returns_200_with_token(self, async_client: AsyncClient) -> None:
        await _register(async_client)
        resp = await _login(async_client)
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    async def test_login_wrong_password_returns_401(self, async_client: AsyncClient) -> None:
        await _register(async_client)
        resp = await _login(async_client, password="wrongpassword")
        assert resp.status_code == 401

    async def test_login_unknown_user_returns_401(self, async_client: AsyncClient) -> None:
        resp = await _login(async_client, email="ghost@example.com")
        assert resp.status_code == 401

    async def test_login_wrong_password_same_message_as_unknown_user(self, async_client: AsyncClient) -> None:
        """No user enumeration — error message must be identical."""
        await _register(async_client)
        bad_pw = await _login(async_client, password="wrongpassword")
        unknown = await _login(async_client, email="ghost@example.com")
        assert bad_pw.json()["detail"] == unknown.json()["detail"]


class TestMe:
    async def test_me_returns_200_with_valid_token(self, async_client: AsyncClient) -> None:
        await _register(async_client)
        login_resp = await _login(async_client)
        token = login_resp.json()["access_token"]

        resp = await async_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "user@example.com"
        assert body["plan"] == "free"
        assert "id" in body

    async def test_me_returns_401_without_token(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/auth/me")
        assert resp.status_code == 401

    async def test_me_returns_401_with_invalid_token(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/auth/me", headers={"Authorization": "Bearer not.a.real.token"})
        assert resp.status_code == 401
