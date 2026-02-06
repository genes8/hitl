import os
import uuid
from datetime import datetime, timedelta, timezone

import psycopg

from src.database import SessionLocal
from src.services.queue_service import QueueService


def _sync_dsn() -> str:
    dsn = os.environ.get("DATABASE_URL")
    assert dsn, "DATABASE_URL must be set in CI"
    return dsn.replace("postgresql+asyncpg://", "postgresql://")


def _create_tenant() -> uuid.UUID:
    tenant_id = uuid.uuid4()
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tenants (id, name, slug) VALUES (%s, %s, %s)",
                (tenant_id, "Test Tenant", f"test-{tenant_id.hex[:8]}"),
            )
        conn.commit()
    return tenant_id


def _create_application(*, tenant_id: uuid.UUID, loan_amount: int) -> uuid.UUID:
    app_id = uuid.uuid4()

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
                    "APP-Q-TEST",
                    "pending",
                    '{"name":"Jane"}',
                    '{"net_monthly_income": 1000}',
                    f'{{"loan_amount": {loan_amount}}}',
                    None,
                    "web",
                    "{}",
                ),
            )
        conn.commit()

    return app_id


def test_queue_service_create_queue_entry_sets_priority_and_sla_deadline():
    tenant_id = _create_tenant()
    app_id = _create_application(tenant_id=tenant_id, loan_amount=5_000_001)

    service = QueueService()

    now = datetime.now(tz=timezone.utc)

    async def _run():
        async with SessionLocal() as session:
            entry = await service.create_queue_entry(
                session,
                application_id=app_id,
                score_at_routing=700,
                routing_reason="borderline_score",
                is_vip=False,
            )
            return entry

    import asyncio

    entry = asyncio.run(_run())

    # amount > 5,000,000 subtracts 15 from baseline 50; SLA exactly 8h => no additional subtraction
    assert entry.priority == 35
    assert entry.routing_reason == "borderline_score"
    assert entry.score_at_routing == 700

    # allow some jitter, but should be ~8 hours from the call.
    assert entry.sla_deadline >= now + timedelta(hours=7, minutes=59)
    assert entry.sla_deadline <= now + timedelta(hours=8, minutes=1)
