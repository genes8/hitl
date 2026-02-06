"""Development seed data.

Idempotent by design: safe to run multiple times.

Usage:
  DATABASE_URL=postgresql+asyncpg://... python -m src.scripts.seed_dev_data

We intentionally keep this script *sync* (psycopg) so it can run in CI and
one-off local dev without needing an async event loop.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg


@dataclass(frozen=True)
class SeedResult:
    tenant_id: uuid.UUID
    admin_user_id: uuid.UUID
    threshold_id: uuid.UUID


def _sync_dsn(database_url: str) -> str:
    # CI/dev uses SQLAlchemy DSN for asyncpg; psycopg expects the sync variant.
    return database_url.replace("postgresql+asyncpg://", "postgresql://")


def seed_dev_data(database_url: str) -> SeedResult:
    """Seed a demo tenant, users, and a default active threshold.

    Creates:
      - tenant slug: demo
      - admin: admin@demo.local
      - analyst: analyst@demo.local
      - default threshold: Default (active)

    Returns IDs for convenience.
    """

    dsn = _sync_dsn(database_url)
    now = datetime.now(timezone.utc)

    tenant_id = uuid.uuid4()
    admin_user_id = uuid.uuid4()
    analyst_user_id = uuid.uuid4()
    threshold_id = uuid.uuid4()

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            # Tenant
            cur.execute(
                """
                INSERT INTO tenants (id, name, slug)
                VALUES (%s, %s, %s)
                ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                (tenant_id, "Demo Bank", "demo"),
            )
            tenant_id = cur.fetchone()[0]

            # Users
            cur.execute(
                """
                INSERT INTO users (id, tenant_id, email, role, first_name, last_name)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (tenant_id, email) DO UPDATE SET role = EXCLUDED.role
                RETURNING id
                """,
                (admin_user_id, tenant_id, "admin@demo.local", "admin", "Demo", "Admin"),
            )
            admin_user_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO users (id, tenant_id, email, role, first_name, last_name)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (tenant_id, email) DO UPDATE SET role = EXCLUDED.role
                RETURNING id
                """,
                (analyst_user_id, tenant_id, "analyst@demo.local", "analyst", "Demo", "Analyst"),
            )
            analyst_user_id = cur.fetchone()[0]

            # Thresholds: ensure exactly one active default threshold in demo tenant.
            cur.execute(
                "UPDATE decision_thresholds SET is_active = false WHERE tenant_id = %s",
                (tenant_id,),
            )

            cur.execute(
                "SELECT id FROM decision_thresholds WHERE tenant_id = %s AND name = %s LIMIT 1",
                (tenant_id, "Default"),
            )
            existing = cur.fetchone()

            if existing:
                threshold_id = existing[0]
                cur.execute(
                    """
                    UPDATE decision_thresholds
                    SET
                      description = %s,
                      auto_approve_min = %s,
                      auto_decline_max = %s,
                      is_active = true,
                      effective_from = %s,
                      approved_by = %s
                    WHERE id = %s
                    """,
                    (
                        "Seeded default routing threshold (dev)",
                        700,
                        500,
                        now,
                        admin_user_id,
                        threshold_id,
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO decision_thresholds (
                        id, tenant_id, name, description,
                        auto_approve_min, auto_decline_max,
                        is_active, effective_from,
                        created_by, approved_by
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        threshold_id,
                        tenant_id,
                        "Default",
                        "Seeded default routing threshold (dev)",
                        700,
                        500,
                        True,
                        now,
                        admin_user_id,
                        admin_user_id,
                    ),
                )
                threshold_id = cur.fetchone()[0]

            conn.commit()

    return SeedResult(tenant_id=tenant_id, admin_user_id=admin_user_id, threshold_id=threshold_id)


def main() -> None:
    database_url = os.environ.get("DATABASE_URL") or os.environ.get("database_url")
    if not database_url:
        raise SystemExit("DATABASE_URL env var is required")

    result = seed_dev_data(database_url)
    print("Seeded dev data:")
    print(f"- tenant_id: {result.tenant_id}")
    print(f"- admin_user_id: {result.admin_user_id}")
    print(f"- threshold_id: {result.threshold_id}")


if __name__ == "__main__":
    main()
