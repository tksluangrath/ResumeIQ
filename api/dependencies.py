from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from engine.extractor import EntityExtractor
from engine.llm import create_llm
from engine.llm.base import BaseLLM
from engine.matcher import SemanticMatcher
from engine.scorer import MatchScorer

_state: dict[str, Any] = {}

PLAN_SCAN_LIMITS: dict[str, int | None] = {
    "free": 5,
    "starter": 25,
    "pro": None,  # None = unlimited
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    from api.db import make_engine

    settings = get_settings()
    _state["extractor"] = EntityExtractor()
    _state["matcher"] = SemanticMatcher()
    if settings.APP_ENV != "production":
        _state["matcher"].encode("warmup")  # forces SentenceTransformer load now, not on first request
    _state["scorer"] = MatchScorer()
    _state["llm"] = create_llm(settings)
    engine, session_factory = make_engine()
    _state["db_engine"] = engine
    _state["db_session_factory"] = session_factory
    yield
    await engine.dispose()
    _state.clear()


def get_extractor() -> EntityExtractor:
    try:
        return _state["extractor"]
    except KeyError:
        raise RuntimeError("EntityExtractor not initialized. Ensure the app lifespan has started.")


def get_matcher() -> SemanticMatcher:
    try:
        return _state["matcher"]
    except KeyError:
        raise RuntimeError("SemanticMatcher not initialized. Ensure the app lifespan has started.")


def get_scorer() -> MatchScorer:
    try:
        return _state["scorer"]
    except KeyError:
        raise RuntimeError("MatchScorer not initialized. Ensure the app lifespan has started.")


def get_llm() -> BaseLLM:
    try:
        return _state["llm"]
    except KeyError:
        raise RuntimeError("BaseLLM not initialized. Ensure the app lifespan has started.")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a per-request DB session. Always closes on exit."""
    factory = _state.get("db_session_factory")
    if factory is None:
        raise RuntimeError("DB session factory not initialized. Ensure the app lifespan has started.")
    async with factory() as session:
        yield session


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any | None:
    """Optional auth — returns User if a valid Bearer token is present, None otherwise.

    Does NOT raise on missing or invalid token; callers decide how to handle None.
    """
    from api.db import User
    from api.security import decode_token

    auth_header: str | None = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token)
    except ValueError:
        return None
    user_id: str = str(payload["sub"])
    result: User | None = await db.get(User, uuid.UUID(user_id))
    if result is None or not result.is_active:
        return None
    return result


async def require_current_user(
    user: Any | None = Depends(get_current_user),
) -> Any:
    """Mandatory auth — raises 401 if no valid user."""
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def check_and_increment_scan(user: Any, db: AsyncSession) -> None:
    """Enforce weekly scan limit, reset counter if 7+ days elapsed, increment on success.

    Raises HTTP 429 if the user is at or over their plan limit.
    """
    now = datetime.now(timezone.utc)
    reset_at = user.scan_reset_at
    if reset_at.tzinfo is None:
        reset_at = reset_at.replace(tzinfo=timezone.utc)

    if (now - reset_at) >= timedelta(days=7):
        user.scan_count = 0
        user.scan_reset_at = now

    if user.scan_credits > 0:
        user.scan_credits -= 1
        await db.commit()
        return

    limit: int | None = PLAN_SCAN_LIMITS.get(user.plan)
    if limit is not None and user.scan_count >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Scan limit reached for {user.plan} plan ({limit}/week). Upgrade to continue.",
        )

    user.scan_count += 1
    await db.commit()
