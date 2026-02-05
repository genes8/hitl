import asyncio
import os

import psycopg

from src.scripts import seed_dev_data


def _sync_dsn() -> str:
    dsn = os.environ.get("DATABASE_URL")
    assert dsn, "DATABASE_URL must be set in CI"
    return dsn.replace("postgresql+asyncpg://", "postgresql://")


def test_seed_dev_data_is_idempotent():
    # Run twice; verify we don't create duplicates.
    asyncio.run(seed_dev_data.main())

    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM tenants WHERE slug = %s", (seed_dev_data.DEMO_TENANT_SLUG,))
            tenant_id = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM tenants WHERE slug = %s", (seed_dev_data.DEMO_TENANT_SLUG,))
            assert cur.fetchone()[0] == 1

            cur.execute(
                "SELECT COUNT(*) FROM users WHERE tenant_id = %s AND email IN (%s, %s)",
                (tenant_id, "admin@demo.local", "analyst@demo.local"),
            )
            assert cur.fetchone()[0] == 2

            cur.execute(
                "SELECT COUNT(*) FROM decision_thresholds WHERE tenant_id = %s AND is_active = true",
                (tenant_id,),
            )
            assert cur.fetchone()[0] == 1

            cur.execute(
                "SELECT COUNT(*) FROM applications WHERE tenant_id = %s AND source = 'seed'",
                (tenant_id,),
            )
            assert cur.fetchone()[0] == 5

    asyncio.run(seed_dev_data.main())

    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM tenants WHERE slug = %s", (seed_dev_data.DEMO_TENANT_SLUG,))
            tenant_id = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM tenants WHERE slug = %s", (seed_dev_data.DEMO_TENANT_SLUG,))
            assert cur.fetchone()[0] == 1

            cur.execute(
                "SELECT COUNT(*) FROM users WHERE tenant_id = %s AND email IN (%s, %s)",
                (tenant_id, "admin@demo.local", "analyst@demo.local"),
            )
            assert cur.fetchone()[0] == 2

            cur.execute(
                "SELECT COUNT(*) FROM decision_thresholds WHERE tenant_id = %s AND is_active = true",
                (tenant_id,),
            )
            assert cur.fetchone()[0] == 1

            cur.execute(
                "SELECT COUNT(*) FROM applications WHERE tenant_id = %s AND source = 'seed'",
                (tenant_id,),
            )
            assert cur.fetchone()[0] == 5
