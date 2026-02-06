import os
import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture(scope="session")
def sync_dsn() -> str:
    """Synchronous (psycopg) DSN derived from async SQLAlchemy DATABASE_URL."""

    dsn = os.environ.get("DATABASE_URL")
    assert dsn, "DATABASE_URL must be set in CI"
    return dsn.replace("postgresql+asyncpg://", "postgresql://")


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def tenant_id(sync_dsn: str) -> uuid.UUID:
    tid = uuid.uuid4()

    with psycopg.connect(sync_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tenants (id, name, slug) VALUES (%s, %s, %s)",
                (tid, "Test Tenant", f"test-{tid.hex[:8]}"),
            )
        conn.commit()

    return tid
