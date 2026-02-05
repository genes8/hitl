import os
import uuid
from datetime import datetime, timedelta, timezone

import psycopg
import pytest


def _sync_dsn() -> str:
    dsn = os.environ.get("DATABASE_URL")
    assert dsn, "DATABASE_URL must be set in CI"
    return dsn.replace("postgresql+asyncpg://", "postgresql://")


def _create_tenant_and_user() -> tuple[uuid.UUID, uuid.UUID]:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tenants (id, name, slug) VALUES (%s, %s, %s)",
                (tenant_id, "Test Tenant", f"test-{tenant_id.hex[:8]}"),
            )
            cur.execute(
                """
                INSERT INTO users (id, tenant_id, email)
                VALUES (%s, %s, %s)
                """,
                (user_id, tenant_id, f"user-{user_id.hex[:8]}@example.com"),
            )
        conn.commit()

    return tenant_id, user_id


def test_calculate_queue_priority_matches_expected_rules():
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT calculate_queue_priority(%s, %s, %s, %s)",
                (700, 1000, True, 24),
            )
            assert cur.fetchone()[0] == 10

            # amount > 5,000,000 subtracts 15 from baseline 50
            cur.execute(
                "SELECT calculate_queue_priority(%s, %s, %s, %s)",
                (700, 5_000_001, False, 24),
            )
            assert cur.fetchone()[0] == 35

            # sla_hours_remaining < 2 subtracts 20
            cur.execute(
                "SELECT calculate_queue_priority(%s, %s, %s, %s)",
                (700, 1000, False, 1.9),
            )
            assert cur.fetchone()[0] == 30


def test_get_active_threshold_returns_latest_effective_active_threshold():
    tenant_id, user_id = _create_tenant_and_user()

    now = datetime.now(tz=timezone.utc)
    older_effective_from = now - timedelta(days=2)
    newer_effective_from = now - timedelta(hours=1)

    older_id = uuid.uuid4()
    newer_id = uuid.uuid4()

    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO decision_thresholds (
                    id, tenant_id, name, auto_approve_min, auto_decline_max,
                    rules, is_active, effective_from, created_by
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    older_id,
                    tenant_id,
                    "Older",
                    700,
                    300,
                    "{}",
                    True,
                    older_effective_from,
                    user_id,
                ),
            )

            cur.execute(
                """
                INSERT INTO decision_thresholds (
                    id, tenant_id, name, auto_approve_min, auto_decline_max,
                    rules, is_active, effective_from, created_by
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    newer_id,
                    tenant_id,
                    "Newer",
                    720,
                    280,
                    "{}",
                    True,
                    newer_effective_from,
                    user_id,
                ),
            )

            cur.execute(
                "SELECT threshold_id, auto_approve_min, auto_decline_max, rules FROM get_active_threshold(%s)",
                (tenant_id,),
            )
            row = cur.fetchone()

        conn.commit()

    assert row is not None
    assert row[0] == newer_id
    assert row[1] == 720
    assert row[2] == 280


def test_sync_application_status_sets_review_when_in_queue_and_overrides_with_decision():
    tenant_id, user_id = _create_tenant_and_user()

    app_id = uuid.uuid4()
    queue_id = uuid.uuid4()
    decision_id = uuid.uuid4()

    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO applications (
                    id, tenant_id, external_id, status,
                    applicant_data, financial_data, loan_request, credit_bureau_data,
                    source, metadata
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    app_id,
                    tenant_id,
                    "APP-TEST",
                    "pending",
                    "{}",
                    "{}",
                    "{}",
                    None,
                    "web",
                    "{}",
                ),
            )

            cur.execute(
                """
                INSERT INTO analyst_queues (
                    id, application_id, analyst_id, priority, status, sla_deadline
                ) VALUES (%s,%s,%s,%s,%s, NOW() + interval '8 hours')
                """,
                (queue_id, app_id, user_id, 50, "pending"),
            )

            cur.execute("SELECT sync_application_status(%s)", (app_id,))
            cur.execute("SELECT status FROM applications WHERE id=%s", (app_id,))
            assert cur.fetchone()[0] == "review"

            cur.execute(
                """
                INSERT INTO decisions (
                    id, application_id, analyst_id, decision_type, decision_outcome
                ) VALUES (%s,%s,%s,%s,%s)
                """,
                (decision_id, app_id, user_id, "analyst_approve", "approved"),
            )

            cur.execute("SELECT sync_application_status(%s)", (app_id,))
            cur.execute("SELECT status FROM applications WHERE id=%s", (app_id,))
            assert cur.fetchone()[0] == "approved"

        conn.commit()


def test_threshold_range_check_constraint_blocks_invalid_ranges():
    tenant_id, user_id = _create_tenant_and_user()

    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.CheckViolation):
                cur.execute(
                    """
                    INSERT INTO decision_thresholds (
                        id, tenant_id, name, auto_approve_min, auto_decline_max,
                        rules, is_active, effective_from, created_by
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s, NOW(), %s)
                    """,
                    (
                        uuid.uuid4(),
                        tenant_id,
                        "Bad Range",
                        300,
                        700,  # violates chk_threshold_range
                        "{}",
                        True,
                        user_id,
                    ),
                )

        conn.rollback()
