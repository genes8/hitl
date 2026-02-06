from __future__ import annotations

from collections.abc import AsyncGenerator
import os
import sys

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.config import settings


_engine_kwargs: dict = {"pool_pre_ping": True}

# NOTE: In CI/pytest we use FastAPI's sync TestClient (AnyIO portal).
# That can run requests across different event loops, and asyncpg connections
# in a pooled engine may be reused across loops, causing:
#   RuntimeError: got Future attached to a different loop
# To keep tests stable, disable pooling under pytest.
# PYTEST_CURRENT_TEST is only set while a test is running; during collection
# the app/modules may already import this file. Use sys.modules as well.
if os.getenv("PYTEST_CURRENT_TEST") or ("pytest" in sys.modules):
    _engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(settings.database_url, **_engine_kwargs)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
