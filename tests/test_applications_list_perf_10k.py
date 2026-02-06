import os
import re
import time
import uuid

import psycopg


def _sync_dsn() -> str:
    dsn = os.environ.get("DATABASE_URL")
    assert dsn, "DATABASE_URL must be set in CI"
    return dsn.replace("postgresql+asyncpg://", "postgresql://")


def _create_tenant(cur) -> uuid.UUID:
    tenant_id = uuid.uuid4()
    cur.execute(
        "INSERT INTO tenants (id, name, slug) VALUES (%s, %s, %s)",
        (tenant_id, "Perf Tenant", f"perf-{tenant_id.hex[:8]}"),
    )
    return tenant_id


def _bulk_insert_applications(cur, *, tenant_id: uuid.UUID, n: int) -> None:
    # Keep JSON payload small to avoid dominating runtime with insert costs.
    applicant = '{"name": "Perf"}'
    financial = '{"net_monthly_income": 1000, "monthly_obligations": 200, "existing_loans_payment": 100}'
    loan = '{"loan_amount": 12000, "estimated_payment": 300}'

    rows = []
    for i in range(n):
        rows.append(
            (
                uuid.uuid4(),
                tenant_id,
                f"APP-PERF-{i}",
                "pending",
                applicant,
                financial,
                loan,
                None,
                "web",
            )
        )

    cur.executemany(
        """
        INSERT INTO applications (
          id, tenant_id, external_id, status,
          applicant_data, financial_data, loan_request,
          credit_bureau_data, source
        ) VALUES (
          %s, %s, %s, %s,
          %s::jsonb, %s::jsonb, %s::jsonb,
          %s, %s
        )
        """.strip(),
        rows,
    )


def _explain_analyze_execution_ms(cur, query: str, params: tuple) -> float:
    cur.execute("EXPLAIN (ANALYZE, BUFFERS) " + query, params)
    plan_lines = [r[0] for r in cur.fetchall()]

    m = None
    for line in plan_lines:
        m = re.search(r"Execution Time: ([0-9.]+) ms", line)
        if m:
            return float(m.group(1))

    raise AssertionError("Could not find Execution Time in EXPLAIN output:\n" + "\n".join(plan_lines))


def test_applications_list_query_executes_under_100ms_for_10k_records():
    # Phase 2.1.2: Performance check for application listing with 10k records.
    # This is a DB-level guardrail (EXPLAIN ANALYZE) to avoid flaky HTTP timing in CI.
    max_ms = float(os.environ.get("HITL_APP_LIST_10K_MAX_MS", "100"))
    n = int(os.environ.get("HITL_APP_LIST_10K_N", "10000"))

    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            tenant_id = _create_tenant(cur)
            conn.commit()

            # Insert in one transaction.
            _bulk_insert_applications(cur, tenant_id=tenant_id, n=n)
            conn.commit()

            # Warm up the buffer cache for a fair-ish steady-state check.
            cur.execute(
                "SELECT id FROM applications WHERE tenant_id=%s ORDER BY created_at DESC, id DESC LIMIT 20",
                (tenant_id,),
            )
            _ = cur.fetchall()

            start = time.perf_counter()
            exec_ms = _explain_analyze_execution_ms(
                cur,
                "SELECT id FROM applications WHERE tenant_id=%s ORDER BY created_at DESC, id DESC LIMIT 20",
                (tenant_id,),
            )
            wall_ms = (time.perf_counter() - start) * 1000

    assert (
        exec_ms <= max_ms
    ), f"Listing query execution time {exec_ms:.2f}ms exceeded budget {max_ms:.2f}ms (wall {wall_ms:.2f}ms)"
