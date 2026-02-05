import os
import uuid

import psycopg
from fastapi.testclient import TestClient

from src.main import app


def _sync_dsn() -> str:
    dsn = os.environ.get("DATABASE_URL")
    assert dsn, "DATABASE_URL must be set in CI"
    return dsn.replace("postgresql+asyncpg://", "postgresql://")


def _create_tenant(name: str = "Test Tenant") -> uuid.UUID:
    tenant_id = uuid.uuid4()
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tenants (id, name, slug) VALUES (%s, %s, %s)",
                (tenant_id, name, f"test-{tenant_id.hex[:8]}"),
            )
        conn.commit()
    return tenant_id


def _create_application(tenant_id: uuid.UUID) -> dict:
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

    r = client.post("/api/v1/applications", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _set_application_status(application_id: str, status: str):
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE applications SET status = %s WHERE id = %s",
                (status, uuid.UUID(application_id)),
            )
        conn.commit()


def test_patch_application_allows_field_updates_when_pending():
    tenant_id = _create_tenant()
    created = _create_application(tenant_id)

    client = TestClient(app)
    r = client.patch(
        f"/api/v1/applications/{created['id']}",
        json={"applicant_data": {"name": "Jane Updated"}},
    )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["applicant_data"]["name"] == "Jane Updated"


def test_patch_application_blocks_field_updates_when_not_pending():
    tenant_id = _create_tenant()
    created = _create_application(tenant_id)

    _set_application_status(created["id"], "review")

    client = TestClient(app)
    r = client.patch(
        f"/api/v1/applications/{created['id']}",
        json={"loan_request": {"loan_amount": 9999, "estimated_payment": 111}},
    )

    assert r.status_code == 400, r.text
    assert "only allowed" in r.json()["detail"]


def test_patch_application_blocks_invalid_status_transition():
    tenant_id = _create_tenant()
    created = _create_application(tenant_id)

    client = TestClient(app)
    r = client.patch(
        f"/api/v1/applications/{created['id']}",
        json={"status": "approved"},
    )

    assert r.status_code == 400, r.text
    assert "invalid status transition" in r.json()["detail"]


def test_delete_application_sets_cancelled_when_pending():
    tenant_id = _create_tenant()
    created = _create_application(tenant_id)

    client = TestClient(app)
    r = client.delete(f"/api/v1/applications/{created['id']}")

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "cancelled"


def test_delete_application_blocks_when_not_pending():
    tenant_id = _create_tenant()
    created = _create_application(tenant_id)

    _set_application_status(created["id"], "review")

    client = TestClient(app)
    r = client.delete(f"/api/v1/applications/{created['id']}")

    assert r.status_code == 400, r.text
    assert "invalid status transition" in r.json()["detail"]
