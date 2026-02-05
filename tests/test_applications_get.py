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


def test_get_application_200():
    tenant_id = _create_tenant()
    created = _create_application(tenant_id)

    client = TestClient(app)
    r = client.get(f"/api/v1/applications/{created['id']}")

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["id"] == created["id"]
    assert data["tenant_id"] == str(tenant_id)


def test_get_application_404_when_tenant_scoping_mismatch():
    tenant_a = _create_tenant("Tenant A")
    tenant_b = _create_tenant("Tenant B")

    created = _create_application(tenant_a)

    client = TestClient(app)
    r = client.get(
        f"/api/v1/applications/{created['id']}",
        params={"tenant_id": str(tenant_b)},
    )

    assert r.status_code == 404, r.text
