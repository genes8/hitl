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


def test_list_applications_searches_by_applicant_name_and_external_id():
    tenant_id = _create_tenant()
    client = TestClient(app)

    created_id = _create_application(client, tenant_id=tenant_id, applicant_name="Marko")

    # external_id is auto-generated; fetch it directly for a deterministic search.
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT external_id FROM applications WHERE id=%s", (created_id,))
            external_id = cur.fetchone()[0]
        conn.commit()

    r1 = client.get(f"/api/v1/applications?tenant_id={tenant_id}&search=Mark")
    assert r1.status_code == 200, r1.text
    assert r1.json()["total"] == 1

    r2 = client.get(f"/api/v1/applications?tenant_id={tenant_id}&search={external_id}")
    assert r2.status_code == 200, r2.text
    assert r2.json()["total"] == 1


def test_list_applications_sorts_by_amount():
    tenant_id = _create_tenant()
    client = TestClient(app)

    # Create two apps with different loan_amount.
    payload_low = {
        "tenant_id": str(tenant_id),
        "external_id": None,
        "applicant_data": {"name": "Low"},
        "financial_data": {
            "net_monthly_income": 1000,
            "monthly_obligations": 200,
            "existing_loans_payment": 100,
        },
        "loan_request": {
            "loan_amount": 1000,
            "estimated_payment": 50,
        },
        "credit_bureau_data": None,
        "source": "web",
    }

    payload_high = {
        **payload_low,
        "applicant_data": {"name": "High"},
        "loan_request": {"loan_amount": 9999, "estimated_payment": 300},
    }

    r_low = client.post("/api/v1/applications", json=payload_low)
    assert r_low.status_code == 201, r_low.text
    low_id = r_low.json()["id"]

    r_high = client.post("/api/v1/applications", json=payload_high)
    assert r_high.status_code == 201, r_high.text
    high_id = r_high.json()["id"]

    r = client.get(f"/api/v1/applications?tenant_id={tenant_id}&sort_by=amount&sort_order=asc")
    assert r.status_code == 200, r.text

    ids = [i["id"] for i in r.json()["items"]]
    assert ids == [low_id, high_id]
