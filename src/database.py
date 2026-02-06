from __future__ import annotations

from collections.abc import AsyncGenerator
import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.config import settings


_engine_kwargs: dict = {"pool_pre_ping": True}

# NOTE: In CI/pytest we use FastAPI's sync TestClient (AnyIO portal).
# That can run requests across different event loops, and asyncpg connections
# in a pooled engine may be reused across loops, causing:
#   RuntimeError: got Future attached to a different loop
# To keep tests stable, disable pooling under pytest.
if os.getenv("PYTEST_CURRENT_TEST"):
    _engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(settings.database_url, **_engine_kwargs)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
