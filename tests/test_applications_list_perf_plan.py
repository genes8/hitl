import os
import uuid

import psycopg


def _sync_dsn() -> str:
    dsn = os.environ.get("DATABASE_URL")
    assert dsn, "DATABASE_URL must be set in CI"
    return dsn.replace("postgresql+asyncpg://", "postgresql://")


def test_list_applications_uses_tenant_created_at_index_for_large_tenant_dataset():
    """Perf guard for TODO-2.1.2.

    Rather than asserting wall-clock latency (flaky in shared CI), we assert
    Postgres chooses an index-based plan for the common tenant-scoped listing
    query once the tenant has many applications.
    """

    tenant_id = uuid.uuid4()
    dsn = _sync_dsn()

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tenants (id, name, slug) VALUES (%s, %s, %s)",
                (tenant_id, "Perf Tenant", f"perf-{tenant_id.hex[:8]}"),
            )

            # Insert 10k rows for this tenant quickly using generate_series.
            cur.execute(
                """
                INSERT INTO applications (
                    id,
                    tenant_id,
                    external_id,
                    status,
                    applicant_data,
                    financial_data,
                    loan_request,
                    credit_bureau_data,
                    source,
                    meta,
                    expires_at,
                    created_at,
                    updated_at
                )
                SELECT
                    ('00000000-0000-0000-0000-' || lpad(gs::text, 12, '0'))::uuid,
                    %(tenant_id)s,
                    'APP-PERF-' || gs::text,
                    'pending',
                    jsonb_build_object('name', 'Perf ' || gs::text),
                    jsonb_build_object(
                        'net_monthly_income', 1000,
                        'monthly_obligations', 200,
                        'existing_loans_payment', 100
                    ),
                    jsonb_build_object(
                        'loan_amount', (1000 + (gs %% 1000)),
                        'estimated_payment', 50
                    ),
                    NULL,
                    'web',
                    jsonb_build_object('derived', jsonb_build_object()),
                    now() + interval '30 days',
                    now() - (gs || ' seconds')::interval,
                    now()
                FROM generate_series(1, 10000) gs
                """,
                {"tenant_id": tenant_id},
            )

            # Common list query shape (sort_by=created_at, desc) for page 1.
            cur.execute(
                """
                EXPLAIN
                SELECT id
                FROM applications
                WHERE tenant_id = %(tenant_id)s
                ORDER BY created_at DESC, id DESC
                LIMIT 20 OFFSET 0
                """,
                {"tenant_id": tenant_id},
            )

            plan_text = "\n".join(r[0] for r in cur.fetchall())

        conn.commit()

    # The exact node type can vary (Index Scan / Bitmap Index Scan), but the
    # index name should appear in the plan when used.
    assert "idx_applications_tenant_created" in plan_text
