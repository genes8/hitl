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


def _create_application(client: TestClient, *, tenant_id: uuid.UUID) -> str:
    payload = {
        "tenant_id": str(tenant_id),
        "external_id": None,
        "applicant_data": {"name": "Jane"},
        "financial_data": {
            "net_monthly_income": 1000,
            "monthly_obligations": 200,
            "existing_loans_payment": 100,
        },
        "loan_request": {"loan_amount": 12000, "estimated_payment": 300},
        "credit_bureau_data": None,
        "source": "web",
    }

    r = client.post("/api/v1/applications", json=payload)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_delete_application_sets_status_cancelled():
    tenant_id = _create_tenant()
    client = TestClient(app)

    app_id = _create_application(client, tenant_id=tenant_id)

    r = client.delete(f"/api/v1/applications/{app_id}")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"


def test_delete_application_is_idempotent_when_already_cancelled():
    tenant_id = _create_tenant()
    client = TestClient(app)

    app_id = _create_application(client, tenant_id=tenant_id)

    r1 = client.delete(f"/api/v1/applications/{app_id}")
    assert r1.status_code == 200, r1.text

    r2 = client.delete(f"/api/v1/applications/{app_id}")
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "cancelled"


def test_delete_application_blocks_cancel_when_not_pending():
    tenant_id = _create_tenant()
    client = TestClient(app)

    app_id = _create_application(client, tenant_id=tenant_id)

    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE applications SET status=%s WHERE id=%s", ("review", app_id))
        conn.commit()

    r = client.delete(f"/api/v1/applications/{app_id}")
    assert r.status_code == 422, r.text
