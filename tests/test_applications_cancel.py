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


def test_delete_application_sets_status_cancelled_and_is_idempotent():
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
        "loan_request": {"loan_amount": 12000, "estimated_payment": 300},
        "credit_bureau_data": None,
        "source": "web",
    }

    created = client.post("/api/v1/applications", json=payload)
    assert created.status_code == 201, created.text

    app_id = created.json()["id"]

    r1 = client.delete(f"/api/v1/applications/{app_id}")
    assert r1.status_code == 200, r1.text
    assert r1.json()["status"] == "cancelled"

    # Second delete should be idempotent.
    r2 = client.delete(f"/api/v1/applications/{app_id}")
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "cancelled"


def test_delete_application_409_when_not_pending():
    tenant_id = _create_tenant()
    client = TestClient(app)

    payload = {
        "tenant_id": str(tenant_id),
        "external_id": "APP-LOCKED",
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

    created = client.post("/api/v1/applications", json=payload)
    assert created.status_code == 201, created.text

    app_id = uuid.UUID(created.json()["id"])

    # Force status out of band to simulate progression.
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE applications SET status='approved' WHERE id=%s", (app_id,))
        conn.commit()

    r = client.delete(f"/api/v1/applications/{app_id}")
    assert r.status_code == 409, r.text
