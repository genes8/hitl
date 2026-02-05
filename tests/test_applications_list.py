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
        "loan_request": {
            "loan_amount": 12000,
            "estimated_payment": 300,
        },
        "credit_bureau_data": None,
        "source": "web",
    }

    r = client.post("/api/v1/applications", json=payload)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_list_applications_returns_items_and_total():
    tenant_id = _create_tenant()
    client = TestClient(app)

    _create_application(client, tenant_id=tenant_id, applicant_name="A")
    _create_application(client, tenant_id=tenant_id, applicant_name="B")

    r = client.get(f"/api/v1/applications?tenant_id={tenant_id}")
    assert r.status_code == 200, r.text

    data = r.json()
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert len(data["items"]) == 2

    for item in data["items"]:
        assert item["tenant_id"] == str(tenant_id)
        assert item["status"] == "pending"
        assert "submitted_at" in item


def test_list_applications_paginates():
    tenant_id = _create_tenant()
    client = TestClient(app)

    _create_application(client, tenant_id=tenant_id, applicant_name="A")
    _create_application(client, tenant_id=tenant_id, applicant_name="B")

    r1 = client.get(f"/api/v1/applications?tenant_id={tenant_id}&page=1&page_size=1")
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert d1["total"] == 2
    assert len(d1["items"]) == 1

    r2 = client.get(f"/api/v1/applications?tenant_id={tenant_id}&page=2&page_size=1")
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    assert d2["total"] == 2
    assert len(d2["items"]) == 1


def test_list_applications_filters_by_status():
    tenant_id = _create_tenant()
    client = TestClient(app)

    a1 = _create_application(client, tenant_id=tenant_id, applicant_name="A")
    _create_application(client, tenant_id=tenant_id, applicant_name="B")

    # Manually update one row to simulate a different lifecycle status.
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE applications SET status = %s WHERE id = %s", ("scoring", a1))
        conn.commit()

    r = client.get(f"/api/v1/applications?tenant_id={tenant_id}&status=scoring")
    assert r.status_code == 200, r.text

    data = r.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["status"] == "scoring"
