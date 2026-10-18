"""Test setup: a separate database, built by running the real Alembic migrations (down then up)."""

import asyncio
import os

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app import security
from app.db import get_session
from app.main import app
from app.repositories import users as users_repo

TEST_URL = os.environ["TEST_DATABASE_URL"]
PASSWORD = "correct horse battery"


def _ensure_database() -> None:
    async def go() -> None:
        server, name = TEST_URL.replace("postgresql+asyncpg", "postgresql").rsplit("/", 1)
        conn = await asyncpg.connect(f"{server}/postgres")
        try:
            if not await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", name):
                await conn.execute(f'CREATE DATABASE "{name}"')
        finally:
            await conn.close()

    asyncio.run(go())


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    _ensure_database()
    cfg = Config("alembic.ini")
    cfg.attributes.update(url=TEST_URL, skip_logging=True)
    command.downgrade(cfg, "base")  # also proves every downgrade works
    command.upgrade(cfg, "head")


@pytest.fixture
async def db():
    """A session factory on the test DB; all user data is wiped after each test (band tables stay)."""
    engine = create_async_engine(TEST_URL, poolclass=NullPool)
    yield async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE users, tests, tags, ai_usage RESTART IDENTITY CASCADE"))
    await engine.dispose()


@pytest.fixture
async def client(db):
    async def override_session():
        async with db() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    security._login_attempts.clear()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def user(db):
    async with db() as session:
        return await users_repo.create(
            session,
            email="Candidate@Example.com",
            password_hash=security.hash_password(PASSWORD),
            display_name="Candidate",
            budget_usd=10,
        )
