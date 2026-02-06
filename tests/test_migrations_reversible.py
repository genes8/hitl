import os

import psycopg
from alembic import command
from alembic.config import Config


def _alembic_config() -> Config:
    cfg = Config("alembic.ini")
    # We rely on env.py to translate async DSN -> sync driver for Alembic.
    return cfg


def test_migrations_are_reversible():
    """Smoke-test: upgrade head -> downgrade base -> upgrade head.

    This gives us confidence that:
    - migrations apply cleanly
    - downgrade steps exist and work
    - re-upgrade is idempotent (from a clean base)

    CI runs against a Postgres service.
    """

    dsn = os.environ.get("DATABASE_URL")
    assert dsn, "DATABASE_URL must be set (CI provides Postgres service)"

    # Ensure we can connect before attempting Alembic.
    sync_dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
    with psycopg.connect(sync_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")

    cfg = _alembic_config()

    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
