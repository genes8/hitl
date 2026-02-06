import os
import uuid

import psycopg
from fastapi.testclient import TestClient

from src.main import app


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


def test_get_application_includes_queue_info_when_present():
    tenant_id = _create_tenant()

    client = TestClient(app)

    payload = {
        "tenant_id": str(tenant_id),
        "external_id": None,
        "applicant_data": {"name": "Jane"},
        "financial_data": {
            "net_monthly_income": 1000,
            "monthly_obligations": 200,
            "existing_loans_payment": 100,
        },
        "loan_request": {
            "loan_amount": 12000,
            "estimated_payment": 300,
        },
        "credit_bureau_data": None,
        "source": "web",
    }

    created = client.post("/api/v1/applications", json=payload)
    assert created.status_code == 201, created.text
    application_id = uuid.UUID(created.json()["id"])

    queue_id = uuid.uuid4()
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO analyst_queues (
                    id,
                    application_id,
                    analyst_id,
                    priority,
                    priority_reason,
                    status,
                    sla_deadline,
                    sla_breached,
                    routing_reason,
                    score_at_routing
                ) VALUES (
                    %s,
                    %s,
                    NULL,
                    %s,
                    %s,
                    %s,
                    NOW() + INTERVAL '8 hours',
                    false,
                    %s,
                    %s
                )
                """,
                (queue_id, application_id, 42, "borderline_score", "pending", "borderline_score", 580),
            )
        conn.commit()

    r = client.get(f"/api/v1/applications/{application_id}", params={"tenant_id": str(tenant_id)})
    assert r.status_code == 200, r.text

    data = r.json()
    assert data["id"] == str(application_id)
    assert data["queue_info"] is not None
    assert data["queue_info"]["id"] == str(queue_id)
    assert data["queue_info"]["application_id"] == str(application_id)
    assert data["queue_info"]["priority"] == 42
    assert data["queue_info"]["status"] == "pending"
