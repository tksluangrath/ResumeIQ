from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set test env vars before any project imports so get_settings() picks them up.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/resumeiq_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/resumeiq_test")
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production-use-only")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRY_MINUTES", "60")

from api.db import Base  # noqa: E402 — must come after env vars are set
from config import get_settings  # noqa: E402


@pytest.fixture(autouse=True, scope="session")
def clear_settings_cache() -> Generator[None, None, None]:
    """Clear the lru_cache on get_settings so test env vars take effect."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create tables, yield engine, drop tables, dispose engine."""
    settings = get_settings()
    engine = create_async_engine(settings.TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Yield a session connected to the test engine."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def async_client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient wired to the FastAPI app with the test DB injected."""
    from api import dependencies
    from api.main import create_app

    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Patch _state after lifespan starts so the app uses the test DB
        dependencies._state["db_session_factory"] = factory
        dependencies._state["db_engine"] = db_engine
        yield client
