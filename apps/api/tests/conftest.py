"""
Test configuration — uses SQLite in-memory DB for all Phase 1+ tests.
No Postgres required in CI.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.rate_limit import reset_for_testing
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(autouse=True)
async def setup_db():
    """Create all tables before each test; drop after. Also resets rate-limit
    windows so test-client calls never get throttled by earlier tests."""
    reset_for_testing()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client():
    """HTTP test client with DB overridden to SQLite."""

    async def override_get_db():
        async with TestSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


_TOTP_TEST_USER = {
    "tenant_name": "Totp Corp",
    "tenant_slug": "totp-corp",
    "workspace_name": "Main",
    "email": "totp@totp-corp.com",
    "password": "totppassword1",
    "full_name": "Totp User",
    "plan": "baseline",
}


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Register a user and return auth headers for TOTP tests."""
    res = await client.post("/api/v1/auth/register", json=_TOTP_TEST_USER)
    assert res.status_code == 201, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


_ADMIN_TEST_USER = {
    "tenant_name": "Schedule Admin Corp",
    "tenant_slug": "schedule-admin-corp",
    "workspace_name": "Admin Workspace",
    "email": "admin@schedule-test.example.com",
    "password": "adminpassword1",
    "full_name": "Schedule Admin",
    "plan": "baseline",
}


@pytest.fixture
async def admin_headers(client: AsyncClient) -> dict:
    """Register an admin (super_admin) user and return auth headers."""
    res = await client.post("/api/v1/auth/register", json=_ADMIN_TEST_USER)
    assert res.status_code == 201, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
