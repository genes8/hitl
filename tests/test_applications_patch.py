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


def test_patch_application_updates_fields_when_pending_and_recomputes_derived_meta():
    tenant_id = _create_tenant()
    client = TestClient(app)

    payload = {
        "tenant_id": str(tenant_id),
        "external_id": "APP-1",
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

    patch_payload = {
        "external_id": "APP-1-UPDATED",
        "financial_data": {
            "net_monthly_income": 2000,
            "monthly_obligations": 100,
            "existing_loans_payment": 50,
        },
    }

    r = client.patch(f"/api/v1/applications/{app_id}", json=patch_payload)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["external_id"] == "APP-1-UPDATED"
    assert body["financial_data"]["net_monthly_income"] == 2000

    # Derived ratios should be updated in meta.derived.
    derived = body.get("meta", {}).get("derived")
    assert derived is not None
    assert abs(derived["dti_ratio"] - ((100 + 50) / 2000.0)) < 1e-9


def test_patch_application_409_when_not_pending():
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

    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE applications SET status='approved' WHERE id=%s", (app_id,))
        conn.commit()

    r = client.patch(f"/api/v1/applications/{app_id}", json={"external_id": "SHOULD-NOT"})
    assert r.status_code == 409, r.text


def test_patch_application_409_for_invalid_status_transition():
    tenant_id = _create_tenant()
    client = TestClient(app)

    payload = {
        "tenant_id": str(tenant_id),
        "external_id": "APP-STATUS",
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

    r = client.patch(f"/api/v1/applications/{app_id}", json={"status": "approved"})
    assert r.status_code == 409, r.text
