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


def test_create_application_201_and_derives_ratios(monkeypatch):
    tenant_id = _create_tenant()

    # Ensure we trigger the scoring enqueue hook on intake.
    called = {"application_id": None}

    from src.worker import dispatch

    def _fake_enqueue_score_application(*, application_id):
        called["application_id"] = application_id

    monkeypatch.setattr(dispatch, "enqueue_score_application", _fake_enqueue_score_application)

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

    data = r.json()
    assert data["tenant_id"] == str(tenant_id)
    assert data["status"] == "pending"
    assert data["external_id"].startswith("APP-")

    derived = data["meta"]["derived"]
    assert derived["dti_ratio"] == 0.3
    assert derived["loan_to_income"] == 1.0
    assert derived["payment_to_income"] == 0.3

    # The dispatcher should have been invoked with the created application id.
    assert called["application_id"] == uuid.UUID(data["id"])


def test_create_application_422_when_missing_required_fields():
    tenant_id = _create_tenant()

    client = TestClient(app)

    payload = {
        "tenant_id": str(tenant_id),
        "external_id": None,
        "applicant_data": {},  # missing name
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
    assert r.status_code == 422, r.text


def test_create_application_422_when_income_non_positive():
    tenant_id = _create_tenant()

    client = TestClient(app)

    payload = {
        "tenant_id": str(tenant_id),
        "external_id": None,
        "applicant_data": {"name": "Jane"},
        "financial_data": {
            "net_monthly_income": 0,
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
    assert r.status_code == 422, r.text
