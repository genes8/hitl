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


def _create_application(client: TestClient, *, tenant_id: uuid.UUID, applicant_name: str) -> None:
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


def test_list_applications_supports_cursor_pagination_created_at_desc():
    tenant_id = _create_tenant()
    client = TestClient(app)

    _create_application(client, tenant_id=tenant_id, applicant_name="A")
    _create_application(client, tenant_id=tenant_id, applicant_name="B")
    _create_application(client, tenant_id=tenant_id, applicant_name="C")

    r1 = client.get(f"/api/v1/applications?tenant_id={tenant_id}&page_size=2")
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert len(d1["items"]) == 2
    assert d1["next_cursor"]

    import urllib.parse

    r2 = client.get(
        f"/api/v1/applications?tenant_id={tenant_id}&page_size=2&cursor={urllib.parse.quote(d1['next_cursor'])}"
    )
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    assert len(d2["items"]) == 1
    assert d2["next_cursor"] is None


def test_list_applications_cursor_requires_sort_by_created_at():
    tenant_id = _create_tenant()
    client = TestClient(app)

    _create_application(client, tenant_id=tenant_id, applicant_name="A")

    r = client.get(
        f"/api/v1/applications?tenant_id={tenant_id}&cursor=2020-01-01T00:00:00+00:00|{uuid.uuid4()}&sort_by=amount"
    )
    assert r.status_code == 422
