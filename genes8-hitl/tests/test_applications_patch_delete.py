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


def _create_application(*, tenant_id: uuid.UUID) -> str:
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
    return created.json()["id"]


def test_patch_application_updates_pending_fields():
    tenant_id = _create_tenant()
    app_id = _create_application(tenant_id=tenant_id)
    client = TestClient(app)

    r = client.patch(
        f"/api/v1/applications/{app_id}?tenant_id={tenant_id}",
        json={"applicant_data": {"name": "Jane Updated"}},
    )
    assert r.status_code == 200, r.text
    assert r.json()["id"] == app_id
    assert r.json()["applicant_data"]["name"] == "Jane Updated"


def test_patch_application_status_to_cancelled():
    tenant_id = _create_tenant()
    app_id = _create_application(tenant_id=tenant_id)
    client = TestClient(app)

    r = client.patch(
        f"/api/v1/applications/{app_id}?tenant_id={tenant_id}",
        json={"status": "cancelled"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"


def test_patch_application_rejects_unsupported_status_transitions():
    tenant_id = _create_tenant()
    app_id = _create_application(tenant_id=tenant_id)
    client = TestClient(app)

    r = client.patch(
        f"/api/v1/applications/{app_id}?tenant_id={tenant_id}",
        json={"status": "approved"},
    )
    assert r.status_code == 422


def test_patch_application_rejects_field_updates_when_not_pending():
    tenant_id = _create_tenant()
    app_id = _create_application(tenant_id=tenant_id)
    client = TestClient(app)

    # cancel first
    r = client.patch(
        f"/api/v1/applications/{app_id}?tenant_id={tenant_id}",
        json={"status": "cancelled"},
    )
    assert r.status_code == 200

    # then attempt to update fields
    r2 = client.patch(
        f"/api/v1/applications/{app_id}?tenant_id={tenant_id}",
        json={"applicant_data": {"name": "Nope"}},
    )
    assert r2.status_code == 422


def test_delete_application_cancels_pending_application():
    tenant_id = _create_tenant()
    app_id = _create_application(tenant_id=tenant_id)
    client = TestClient(app)

    d = client.delete(f"/api/v1/applications/{app_id}?tenant_id={tenant_id}")
    assert d.status_code == 204, d.text

    r = client.get(f"/api/v1/applications/{app_id}?tenant_id={tenant_id}")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"
