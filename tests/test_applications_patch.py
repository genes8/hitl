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


def _create_application(client: TestClient, *, tenant_id: uuid.UUID, applicant_name: str) -> str:
    payload = {
        "tenant_id": str(tenant_id),
        "external_id": None,
        "applicant_data": {"name": applicant_name},
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


def test_patch_application_allows_pending_field_updates_and_recomputes_derived():
    tenant_id = _create_tenant()
    client = TestClient(app)

    app_id = _create_application(client, tenant_id=tenant_id, applicant_name="Jane")

    patch = {
        "applicant_data": {"name": "Jane Updated"},
        "financial_data": {
            "net_monthly_income": 2000,
            "monthly_obligations": 100,
            "existing_loans_payment": 100,
        },
        "loan_request": {"loan_amount": 12000, "estimated_payment": 400},
    }

    r = client.patch(f"/api/v1/applications/{app_id}", json=patch)
    assert r.status_code == 200, r.text

    data = r.json()
    assert data["applicant_data"]["name"] == "Jane Updated"

    derived = data["meta"]["derived"]
    assert derived["dti_ratio"] == 0.1
    assert derived["loan_to_income"] == 0.5
    assert derived["payment_to_income"] == 0.2


def test_patch_application_allows_pending_to_cancelled():
    tenant_id = _create_tenant()
    client = TestClient(app)

    app_id = _create_application(client, tenant_id=tenant_id, applicant_name="Jane")

    r = client.patch(f"/api/v1/applications/{app_id}", json={"status": "cancelled"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"


def test_patch_application_blocks_invalid_status_transition():
    tenant_id = _create_tenant()
    client = TestClient(app)

    app_id = _create_application(client, tenant_id=tenant_id, applicant_name="Jane")

    r = client.patch(f"/api/v1/applications/{app_id}", json={"status": "approved"})
    assert r.status_code == 422, r.text


def test_patch_application_blocks_field_updates_when_not_pending():
    tenant_id = _create_tenant()
    client = TestClient(app)

    app_id = _create_application(client, tenant_id=tenant_id, applicant_name="Jane")

    # Move status out of pending.
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE applications SET status=%s WHERE id=%s", ("review", app_id))
        conn.commit()

    r = client.patch(
        f"/api/v1/applications/{app_id}",
        json={"applicant_data": {"name": "Nope"}},
    )
    assert r.status_code == 422, r.text
