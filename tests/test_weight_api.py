"""
Tests for the Weight Log API.

Tests weight log CRUD operations via the FastAPI test client.
Uses direct DB inserts for user setup to avoid multi-request session issues.
"""

import uuid
from datetime import date as date_type

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.database import Base
from app.db.models import UserModel

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@pytest_asyncio.fixture(scope="module")
async def test_engine():
    """Module-scoped in-memory DB engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    import app.db.models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="module")
async def session_factory(test_engine: AsyncEngine):
    """Module-scoped session factory."""
    return async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def test_db(session_factory):
    """Per-test session."""
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_db: AsyncSession, session_factory):
    """AsyncClient with DB dependency overridden to use test DB."""
    from app.core.database import get_db

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _seed_user(session_factory, user_id: str) -> None:
    """Insert a test user directly into the database."""
    async with session_factory() as session:
        user = UserModel(
            id=user_id,
            name="Test User",
            email=f"{user_id[:8]}@test.com",
            hashed_password="test-hash-placeholder",
            gender="male",
            birth_date=date_type(1995, 1, 1),
            height_cm=175.0,
            weight_kg=75.0,
            goal="fat_loss",
            activity_level="moderate",
            training_days_per_week=4,
        )
        session.add(user)
        await session.commit()


# ---------- Tests ----------

@pytest.mark.asyncio
async def test_create_weight_log(client: AsyncClient, session_factory):
    """Test creating a weight log entry."""
    user_id = str(uuid.uuid4())
    await _seed_user(session_factory, user_id)

    payload = {
        "user_id": user_id,
        "date": "2024-01-15",
        "weight_kg": 75.5,
        "body_fat_pct": 18.0,
        "notes": "Morning measurement"
    }
    resp = await client.post("/api/weights/", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["user_id"] == user_id
    assert data["weight_kg"] == 75.5
    assert data["body_fat_pct"] == 18.0
    assert data["date"] == "2024-01-15"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_weight_history(client: AsyncClient, session_factory):
    """Test retrieving weight history for a user."""
    user_id = str(uuid.uuid4())
    await _seed_user(session_factory, user_id)

    dates = ["2024-01-10", "2024-01-11", "2024-01-12"]
    for i, d in enumerate(dates):
        resp = await client.post("/api/weights/", json={
            "user_id": user_id,
            "date": d,
            "weight_kg": 80.0 - i * 0.3,
        })
        assert resp.status_code == 201, resp.text

    resp = await client.get(f"/api/weights/user/{user_id}?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_get_latest_weight(client: AsyncClient, session_factory):
    """Test retrieving the latest weight for a user."""
    user_id = str(uuid.uuid4())
    await _seed_user(session_factory, user_id)

    for d, w in [("2024-02-01", 70.0), ("2024-02-05", 69.5)]:
        await client.post("/api/weights/", json={
            "user_id": user_id,
            "date": d,
            "weight_kg": w,
        })

    resp = await client.get(f"/api/weights/user/{user_id}/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["weight_kg"] == 69.5
    assert data["date"] == "2024-02-05"


@pytest.mark.asyncio
async def test_get_weight_range(client: AsyncClient, session_factory):
    """Test querying weight logs by date range."""
    user_id = str(uuid.uuid4())
    await _seed_user(session_factory, user_id)

    for d, w in [("2024-03-01", 72.0), ("2024-03-10", 71.5), ("2024-03-20", 71.0)]:
        await client.post("/api/weights/", json={
            "user_id": user_id,
            "date": d,
            "weight_kg": w,
        })

    resp = await client.get(
        f"/api/weights/user/{user_id}/range?start=2024-03-05&end=2024-03-15"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["date"] == "2024-03-10"


@pytest.mark.asyncio
async def test_delete_weight_log(client: AsyncClient, session_factory):
    """Test deleting a weight log entry."""
    user_id = str(uuid.uuid4())
    await _seed_user(session_factory, user_id)

    resp = await client.post("/api/weights/", json={
        "user_id": user_id,
        "date": "2024-04-01",
        "weight_kg": 68.0,
    })
    assert resp.status_code == 201
    log_id = resp.json()["id"]

    # Delete
    del_resp = await client.delete(f"/api/weights/{log_id}")
    assert del_resp.status_code == 204

    # Verify gone
    history_resp = await client.get(f"/api/weights/user/{user_id}?limit=10")
    assert history_resp.status_code == 200
    assert len(history_resp.json()) == 0


@pytest.mark.asyncio
async def test_weight_log_user_not_found(client: AsyncClient):
    """Test that weight endpoints return 404 for missing users."""
    resp = await client.post("/api/weights/", json={
        "user_id": str(uuid.uuid4()),
        "date": "2024-01-01",
        "weight_kg": 70.0,
    })
    assert resp.status_code == 404

    resp = await client.get(f"/api/weights/user/{uuid.uuid4()}/latest")
    assert resp.status_code == 404
