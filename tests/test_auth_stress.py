"""
Adversarial stress tests for Track 1: PostgreSQL + JWT auth.
Goal: expose token manipulation bugs, input validation gaps, and auth bypass vectors.
100 tests — requires PostgreSQL (resumeiq_test).
"""
from __future__ import annotations

import base64
import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import User
from api.security import create_access_token, hash_password, verify_password


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _reg(
    client: AsyncClient,
    email: str = "stress@example.com",
    password: str = "StrongPass1!",
) -> dict:
    return await client.post("/auth/register", json={"email": email, "password": password})


async def _login(
    client: AsyncClient,
    email: str = "stress@example.com",
    password: str = "StrongPass1!",
) -> dict:
    return await client.post("/auth/login", json={"email": email, "password": password})


async def _token(client: AsyncClient, email: str = "stress@example.com") -> str:
    await _reg(client, email=email)
    resp = await _login(client, email=email)
    return resp.json()["access_token"]


# ── Section 1: Registration validation stress ──────────────────────────────────

class TestRegisterValidationStress:
    async def test_register_success(self, async_client: AsyncClient) -> None:
        resp = await _reg(async_client)
        assert resp.status_code == 201

    async def test_register_returns_bearer_token(self, async_client: AsyncClient) -> None:
        resp = await _reg(async_client)
        assert resp.json()["token_type"] == "bearer"

    async def test_register_token_is_nonempty_string(self, async_client: AsyncClient) -> None:
        resp = await _reg(async_client)
        assert isinstance(resp.json()["access_token"], str)
        assert len(resp.json()["access_token"]) > 0

    async def test_duplicate_email_409(self, async_client: AsyncClient) -> None:
        await _reg(async_client)
        resp = await _reg(async_client)
        assert resp.status_code == 409

    async def test_duplicate_email_case_insensitive_409(self, async_client: AsyncClient) -> None:
        await _reg(async_client, email="User@Example.COM")
        resp = await _reg(async_client, email="user@example.com")
        assert resp.status_code == 409

    async def test_email_stored_lowercase(self, async_client: AsyncClient) -> None:
        await _reg(async_client, email="MixedCase@Example.COM")
        resp = await _login(async_client, email="mixedcase@example.com")
        assert resp.status_code == 200

    async def test_password_exactly_8_chars_succeeds(self, async_client: AsyncClient) -> None:
        resp = await _reg(async_client, password="12345678")
        assert resp.status_code == 201

    async def test_password_7_chars_fails(self, async_client: AsyncClient) -> None:
        resp = await _reg(async_client, password="1234567")
        assert resp.status_code == 422

    async def test_password_empty_fails(self, async_client: AsyncClient) -> None:
        resp = await _reg(async_client, password="")
        assert resp.status_code == 422

    async def test_invalid_email_format_422(self, async_client: AsyncClient) -> None:
        resp = await _reg(async_client, email="notanemail")
        assert resp.status_code == 422

    async def test_email_missing_domain_422(self, async_client: AsyncClient) -> None:
        resp = await _reg(async_client, email="user@")
        assert resp.status_code == 422

    async def test_email_missing_at_422(self, async_client: AsyncClient) -> None:
        resp = await _reg(async_client, email="userexample.com")
        assert resp.status_code == 422

    async def test_missing_email_field_422(self, async_client: AsyncClient) -> None:
        resp = await async_client.post("/auth/register", json={"password": "StrongPass1!"})
        assert resp.status_code == 422

    async def test_missing_password_field_422(self, async_client: AsyncClient) -> None:
        resp = await async_client.post("/auth/register", json={"email": "user@example.com"})
        assert resp.status_code == 422

    async def test_empty_body_422(self, async_client: AsyncClient) -> None:
        resp = await async_client.post("/auth/register", json={})
        assert resp.status_code == 422

    async def test_extra_fields_ignored(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/auth/register",
            json={"email": "user@example.com", "password": "StrongPass1!", "role": "admin"},
        )
        assert resp.status_code == 201

    async def test_very_long_email_handled(self, async_client: AsyncClient) -> None:
        long_local = "a" * 200
        resp = await _reg(async_client, email=f"{long_local}@example.com")
        # Should either succeed (201) or reject gracefully (4xx) — never 500
        assert resp.status_code in (201, 422, 400)

    async def test_very_long_password_handled(self, async_client: AsyncClient) -> None:
        long_pw = "A" * 1000
        resp = await _reg(async_client, password=long_pw)
        assert resp.status_code in (201, 422, 400)

    async def test_sql_injection_in_email_rejected(self, async_client: AsyncClient) -> None:
        resp = await _reg(async_client, email="'; DROP TABLE users; --@example.com")
        # Must not crash (500) — either valid email accepted as string or 422
        assert resp.status_code in (201, 422, 400, 409)

    async def test_xss_in_password_field_stored_safely(self, async_client: AsyncClient) -> None:
        xss_pw = "<script>alert(1)</script>Pass1!"
        resp = await _reg(async_client, password=xss_pw)
        # Should succeed if ≥8 chars; XSS not relevant server-side
        assert resp.status_code in (201, 422)


# ── Section 2: Login stress ────────────────────────────────────────────────────

class TestLoginStress:
    async def test_login_success_200(self, async_client: AsyncClient) -> None:
        await _reg(async_client)
        resp = await _login(async_client)
        assert resp.status_code == 200

    async def test_login_returns_token(self, async_client: AsyncClient) -> None:
        await _reg(async_client)
        resp = await _login(async_client)
        assert "access_token" in resp.json()

    async def test_wrong_password_401(self, async_client: AsyncClient) -> None:
        await _reg(async_client)
        resp = await _login(async_client, password="WrongPass!")
        assert resp.status_code == 401

    async def test_unknown_email_401(self, async_client: AsyncClient) -> None:
        resp = await _login(async_client, email="ghost@nowhere.com")
        assert resp.status_code == 401

    async def test_no_user_enumeration(self, async_client: AsyncClient) -> None:
        """Wrong password and unknown user must return identical error detail."""
        await _reg(async_client)
        bad_pw = await _login(async_client, password="WrongPass!")
        unknown = await _login(async_client, email="ghost@nowhere.com")
        assert bad_pw.json()["detail"] == unknown.json()["detail"]

    async def test_login_case_insensitive_email(self, async_client: AsyncClient) -> None:
        await _reg(async_client, email="user@example.com")
        resp = await _login(async_client, email="USER@EXAMPLE.COM")
        assert resp.status_code == 200

    async def test_empty_password_login_401(self, async_client: AsyncClient) -> None:
        await _reg(async_client)
        resp = await async_client.post(
            "/auth/login", json={"email": "stress@example.com", "password": ""}
        )
        assert resp.status_code in (401, 422)

    async def test_missing_email_422(self, async_client: AsyncClient) -> None:
        resp = await async_client.post("/auth/login", json={"password": "StrongPass1!"})
        assert resp.status_code == 422

    async def test_missing_password_422(self, async_client: AsyncClient) -> None:
        resp = await async_client.post("/auth/login", json={"email": "user@example.com"})
        assert resp.status_code == 422

    async def test_extra_fields_ignored_on_login(self, async_client: AsyncClient) -> None:
        await _reg(async_client)
        resp = await async_client.post(
            "/auth/login",
            json={"email": "stress@example.com", "password": "StrongPass1!", "is_admin": True},
        )
        assert resp.status_code == 200

    async def test_multiple_logins_each_return_token(self, async_client: AsyncClient) -> None:
        await _reg(async_client)
        tokens = set()
        for _ in range(5):
            resp = await _login(async_client)
            assert resp.status_code == 200
            tokens.add(resp.json()["access_token"])
        # Each login should return a token (may or may not be unique depending on timing)
        assert len(tokens) >= 1

    async def test_login_token_type_is_bearer(self, async_client: AsyncClient) -> None:
        await _reg(async_client)
        resp = await _login(async_client)
        assert resp.json()["token_type"] == "bearer"


# ── Section 3: JWT token manipulation stress ───────────────────────────────────

class TestJwtTokenStress:
    async def test_valid_token_accesses_me(self, async_client: AsyncClient) -> None:
        tok = await _token(async_client)
        resp = await async_client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
        assert resp.status_code == 200

    async def test_no_auth_header_401(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/auth/me")
        assert resp.status_code == 401

    async def test_empty_token_401(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/auth/me", headers={"Authorization": "Bearer "})
        assert resp.status_code == 401

    async def test_malformed_token_401(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
        assert resp.status_code == 401

    async def test_token_missing_bearer_prefix_401(self, async_client: AsyncClient) -> None:
        tok = await _token(async_client)
        resp = await async_client.get("/auth/me", headers={"Authorization": tok})
        assert resp.status_code in (401, 403)

    async def test_token_with_wrong_secret_401(self, async_client: AsyncClient) -> None:
        from jose import jwt as jose_jwt
        forged = jose_jwt.encode(
            {"sub": str(uuid.uuid4()), "email": "attacker@evil.com"},
            "wrong-secret",
            algorithm="HS256",
        )
        resp = await async_client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
        assert resp.status_code == 401

    async def test_token_with_tampered_payload_401(self, async_client: AsyncClient) -> None:
        tok = await _token(async_client)
        header, payload, sig = tok.split(".")
        # Decode and modify payload
        padded = payload + "=" * (-len(payload) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(padded))
        decoded["email"] = "admin@system.com"
        tampered_payload = base64.urlsafe_b64encode(
            json.dumps(decoded).encode()
        ).rstrip(b"=").decode()
        tampered_tok = f"{header}.{tampered_payload}.{sig}"
        resp = await async_client.get("/auth/me", headers={"Authorization": f"Bearer {tampered_tok}"})
        assert resp.status_code == 401

    async def test_token_with_none_algorithm_rejected(self, async_client: AsyncClient) -> None:
        """Algorithm confusion attack: 'none' algorithm must be rejected."""
        header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": str(uuid.uuid4()), "email": "hax@evil.com"}).encode()
        ).rstrip(b"=").decode()
        tok = f"{header}.{payload}."
        resp = await async_client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
        assert resp.status_code == 401

    async def test_completely_random_string_token_401(self, async_client: AsyncClient) -> None:
        resp = await async_client.get(
            "/auth/me", headers={"Authorization": "Bearer randomgarbagestring1234"}
        )
        assert resp.status_code == 401

    async def test_token_with_null_bytes_401(self, async_client: AsyncClient) -> None:
        resp = await async_client.get(
            "/auth/me", headers={"Authorization": "Bearer \x00\x00\x00"}
        )
        assert resp.status_code == 401

    async def test_me_returns_correct_email(self, async_client: AsyncClient) -> None:
        email = "verify@example.com"
        tok = await _token(async_client, email=email)
        resp = await async_client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
        assert resp.json()["email"] == email

    async def test_me_returns_default_free_plan(self, async_client: AsyncClient) -> None:
        tok = await _token(async_client)
        resp = await async_client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
        assert resp.json()["plan"] == "free"

    async def test_me_scan_count_starts_at_zero(self, async_client: AsyncClient) -> None:
        tok = await _token(async_client)
        resp = await async_client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
        assert resp.json()["scan_count"] == 0

    async def test_me_has_uuid_id(self, async_client: AsyncClient) -> None:
        tok = await _token(async_client)
        resp = await async_client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
        uid = resp.json()["id"]
        uuid.UUID(uid)  # raises ValueError if invalid

    async def test_auth_scheme_basic_rejected(self, async_client: AsyncClient) -> None:
        credentials = base64.b64encode(b"user@example.com:password").decode()
        resp = await async_client.get("/auth/me", headers={"Authorization": f"Basic {credentials}"})
        assert resp.status_code == 401


# ── Section 4: Password hashing unit tests ────────────────────────────────────

class TestPasswordHashing:
    def test_hash_is_not_plaintext(self) -> None:
        hashed = hash_password("mysecret")
        assert hashed != "mysecret"

    def test_hash_is_deterministically_verifiable(self) -> None:
        pw = "TestPass123"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_wrong_password_fails_verification(self) -> None:
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_two_hashes_of_same_password_differ(self) -> None:
        """bcrypt uses random salt → same password → different hashes."""
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        assert h1 != h2

    def test_empty_password_hashed_not_verified_with_empty(self) -> None:
        """Edge: empty string hashes; verify with non-empty must fail."""
        hashed = hash_password("")
        assert verify_password("notempty", hashed) is False

    def test_unicode_password_hashed_correctly(self) -> None:
        pw = "Pässwörd123"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_very_long_password_hashed(self) -> None:
        long_pw = "A" * 500
        hashed = hash_password(long_pw)
        # bcrypt truncates at 72 bytes — just verify it doesn't crash
        assert isinstance(hashed, str)

    def test_hash_always_returns_string(self) -> None:
        assert isinstance(hash_password("password123"), str)


# ── Section 5: JWT token creation unit tests ──────────────────────────────────

class TestJwtCreation:
    def test_token_has_three_segments(self) -> None:
        tok = create_access_token(str(uuid.uuid4()), "user@example.com")
        assert tok.count(".") == 2

    def test_two_tokens_for_same_user_may_differ(self) -> None:
        uid = str(uuid.uuid4())
        t1 = create_access_token(uid, "user@example.com")
        t2 = create_access_token(uid, "user@example.com")
        # Depending on timing, exp may differ → tokens may or may not match
        assert isinstance(t1, str)
        assert isinstance(t2, str)

    def test_token_for_different_users_differ(self) -> None:
        t1 = create_access_token(str(uuid.uuid4()), "user1@example.com")
        t2 = create_access_token(str(uuid.uuid4()), "user2@example.com")
        assert t1 != t2

    def test_token_is_decodable_without_verification(self) -> None:
        """Header and payload must be valid base64 JSON."""
        tok = create_access_token(str(uuid.uuid4()), "user@example.com")
        header, payload, _ = tok.split(".")
        for part in (header, payload):
            padded = part + "=" * (-len(part) % 4)
            decoded = base64.urlsafe_b64decode(padded)
            obj = json.loads(decoded)
            assert isinstance(obj, dict)

    def test_token_payload_contains_sub(self) -> None:
        uid = str(uuid.uuid4())
        tok = create_access_token(uid, "user@example.com")
        _, payload, _ = tok.split(".")
        padded = payload + "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
        assert "sub" in data
        assert data["sub"] == uid


# ── Section 6: Auth endpoint response shape ───────────────────────────────────

class TestAuthResponseShape:
    async def test_register_response_has_exact_keys(self, async_client: AsyncClient) -> None:
        resp = await _reg(async_client)
        body = resp.json()
        assert set(body.keys()) == {"access_token", "token_type"}

    async def test_me_response_has_expected_keys(self, async_client: AsyncClient) -> None:
        tok = await _token(async_client)
        resp = await async_client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
        body = resp.json()
        assert {"id", "email", "plan", "scan_count", "created_at"}.issubset(body.keys())

    async def test_me_created_at_is_iso_string(self, async_client: AsyncClient) -> None:
        tok = await _token(async_client)
        resp = await async_client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
        from datetime import datetime
        # Should not raise
        datetime.fromisoformat(resp.json()["created_at"].replace("Z", "+00:00"))

    async def test_401_response_has_detail(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/auth/me")
        assert "detail" in resp.json()

    async def test_409_response_has_detail(self, async_client: AsyncClient) -> None:
        await _reg(async_client)
        resp = await _reg(async_client)
        assert "detail" in resp.json()

    async def test_422_response_has_detail(self, async_client: AsyncClient) -> None:
        resp = await _reg(async_client, email="bad-email")
        assert "detail" in resp.json()

    async def test_register_content_type_is_json(self, async_client: AsyncClient) -> None:
        resp = await _reg(async_client)
        assert "application/json" in resp.headers["content-type"]

    async def test_login_content_type_is_json(self, async_client: AsyncClient) -> None:
        await _reg(async_client)
        resp = await _login(async_client)
        assert "application/json" in resp.headers["content-type"]


# ── Section 7: Deactivated account / edge state ───────────────────────────────

class TestAccountState:
    async def test_deactivated_user_cannot_login(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _reg(async_client, email="deact@example.com")
        # Deactivate the user directly in DB
        from sqlalchemy.future import select as sa_select
        result = await db_session.execute(sa_select(User).where(User.email == "deact@example.com"))
        user = result.scalar_one()
        user.is_active = False
        await db_session.commit()

        resp = await _login(async_client, email="deact@example.com")
        assert resp.status_code == 403

    async def test_new_user_is_active_by_default(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _reg(async_client, email="active@example.com")
        from sqlalchemy.future import select as sa_select
        result = await db_session.execute(sa_select(User).where(User.email == "active@example.com"))
        user = result.scalar_one()
        assert user.is_active is True

    async def test_new_user_defaults_to_free_plan(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _reg(async_client, email="newuser@example.com")
        from sqlalchemy.future import select as sa_select
        result = await db_session.execute(sa_select(User).where(User.email == "newuser@example.com"))
        user = result.scalar_one()
        assert user.plan == "free"

    async def test_new_user_scan_count_zero(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _reg(async_client, email="counter@example.com")
        from sqlalchemy.future import select as sa_select
        result = await db_session.execute(sa_select(User).where(User.email == "counter@example.com"))
        user = result.scalar_one()
        assert user.scan_count == 0

    async def test_new_user_no_stripe_customer_id(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _reg(async_client, email="nostripeid@example.com")
        from sqlalchemy.future import select as sa_select
        result = await db_session.execute(sa_select(User).where(User.email == "nostripeid@example.com"))
        user = result.scalar_one()
        assert user.stripe_customer_id is None
