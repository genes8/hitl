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


def test_get_application_200_after_create():
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

    r = client.get(f"/api/v1/applications/{app_id}")
    assert r.status_code == 200, r.text
    assert r.json()["id"] == app_id
    assert r.json()["tenant_id"] == str(tenant_id)


def test_get_application_404_when_unknown_uuid():
    client = TestClient(app)
    unknown = uuid.uuid4()

    r = client.get(f"/api/v1/applications/{unknown}")
    assert r.status_code == 404


def test_get_application_404_when_bad_id_format():
    client = TestClient(app)

    r = client.get("/api/v1/applications/not-a-uuid")
    assert r.status_code == 404
