import os

import psycopg

from src.scripts.seed_dev_data import seed_dev_data


def _sync_dsn() -> str:
    dsn = os.environ.get("DATABASE_URL")
    assert dsn, "DATABASE_URL must be set in CI"
    return dsn.replace("postgresql+asyncpg://", "postgresql://")


def test_seed_dev_data_is_idempotent_and_creates_demo_tenant_and_users():
    database_url = os.environ["DATABASE_URL"]

    # Run twice to assert idempotency.
    r1 = seed_dev_data(database_url)
    r2 = seed_dev_data(database_url)

    assert r1.tenant_id == r2.tenant_id

    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM tenants WHERE slug = %s", ("demo",))
            tenant = cur.fetchone()
            assert tenant is not None
            assert str(tenant[0]) == str(r1.tenant_id)

            cur.execute(
                "SELECT COUNT(*) FROM users WHERE tenant_id = %s AND email IN (%s, %s)",
                (r1.tenant_id, "admin@demo.local", "analyst@demo.local"),
            )
            assert cur.fetchone()[0] == 2

            cur.execute(
                """
                SELECT COUNT(*)
                FROM decision_thresholds
                WHERE tenant_id = %s AND name = %s AND is_active = true
                """,
                (r1.tenant_id, "Default"),
            )
            assert cur.fetchone()[0] == 1
