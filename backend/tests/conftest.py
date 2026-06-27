import os

# Must be set before any app module is imported so Settings() and engine
# creation pick up the test values on first call.
os.environ["TESTING"] = "1"
os.environ["LOADS_API_KEY"] = "test-api-key-abc123"
os.environ["FMCSA_API_KEY"] = "test-fmcsa-abc123"
os.environ["READ_API_KEY"]   = "test-read-key-xyz789"

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.db.database import Base, get_db
from app.db.models import Call, Load, NegotiationEvent  # noqa: F401 — registers models with Base
from app.db.seed import SEED_LOADS
from app.main import app

TEST_API_KEY  = "test-api-key-abc123"
TEST_READ_KEY = "test-read-key-xyz789"


def _override_get_settings() -> Settings:
    return Settings(
        LOADS_API_KEY=TEST_API_KEY,
        FMCSA_API_KEY="test-fmcsa-abc123",
        READ_API_KEY=TEST_READ_KEY,
    )


@pytest_asyncio.fixture
async def client(tmp_path):
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    engine = create_async_engine(db_url, echo=False)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with maker() as session:
        for data in SEED_LOADS:
            session.add(Load(**data))
        await session.commit()

    async def _get_db_override() -> AsyncSession:
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_settings] = _override_get_settings

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
    await engine.dispose()
