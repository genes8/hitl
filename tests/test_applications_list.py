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


def test_list_applications_paginates_and_filters_by_tenant():
    tenant_id = _create_tenant()

    client = TestClient(app)

    base_payload = {
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

    for _ in range(3):
        r = client.post("/api/v1/applications", json=base_payload)
        assert r.status_code == 201, r.text

    other_tenant_id = _create_tenant()
    other_payload = dict(base_payload)
    other_payload["tenant_id"] = str(other_tenant_id)
    r_other = client.post("/api/v1/applications", json=other_payload)
    assert r_other.status_code == 201, r_other.text

    page1 = client.get(
        "/api/v1/applications",
        params={"tenant_id": str(tenant_id), "page": 1, "page_size": 2},
    )
    assert page1.status_code == 200, page1.text
    body1 = page1.json()
    assert body1["total"] == 3
    assert body1["page"] == 1
    assert body1["page_size"] == 2
    assert len(body1["items"]) == 2

    page2 = client.get(
        "/api/v1/applications",
        params={"tenant_id": str(tenant_id), "page": 2, "page_size": 2},
    )
    assert page2.status_code == 200, page2.text
    body2 = page2.json()
    assert body2["total"] == 3
    assert body2["page"] == 2
    assert len(body2["items"]) == 1

    # With no tenant filter, we should see 4 total.
    all_apps = client.get("/api/v1/applications")
    assert all_apps.status_code == 200, all_apps.text
    assert all_apps.json()["total"] >= 4
