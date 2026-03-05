"""
FakeBuster AI — Test Configuration
Fixtures for async test client, mock DB, mock Redis, mock ClamAV.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


# ── Test-specific async engine (SQLite in-memory) ──
TEST_DATABASE_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="function")
async def test_app():
    """
    Create a test FastAPI app with mocked dependencies
    and a test-specific SQLite database.
    """
    # Import Base and models so metadata knows about all tables
    from app.database import Base
    import app.models.user  # noqa: F401 — registers User table
    import app.models.analysis  # noqa: F401 — registers Analysis table

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Mock Redis
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.eval = AsyncMock(return_value=10)  # rate limiter returns "allowed"
    mock_redis.close = AsyncMock()

    # Mock virus scanner with correct enum type
    from app.core.virus_scanner import ScanResult, ScanStatus

    with patch("app.core.rate_limiter.init_redis", return_value=mock_redis), \
         patch("app.core.rate_limiter.close_redis", new_callable=AsyncMock), \
         patch("app.core.rate_limiter.get_redis", return_value=mock_redis), \
         patch("app.core.rate_limiter._redis_client", mock_redis), \
         patch("app.core.virus_scanner.virus_scanner") as mock_scanner:

        mock_scanner.connect.return_value = True
        mock_scanner.is_available.return_value = True
        mock_scanner.scan_file.return_value = ScanResult(
            status=ScanStatus.CLEAN, detail=""
        )

        # Override the get_db dependency to use the test database
        from app.database import get_db
        from app.main import app

        async def override_get_db():
            async with test_session_factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        app.dependency_overrides[get_db] = override_get_db

        yield app

        # Cleanup
        app.dependency_overrides.clear()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(test_app):
    """Async HTTP test client."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
