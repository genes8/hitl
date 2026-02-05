import os
import uuid

import psycopg
from fastapi.testclient import TestClient

from src.main import app


def _sync_dsn() -> str:
    dsn = os.environ.get("DATABASE_URL")
    assert dsn, "DATABASE_URL must be set in CI"
    return dsn.replace("postgresql+asyncpg://", "postgresql://")


def _create_tenant(*, name: str = "Test Tenant") -> uuid.UUID:
    tenant_id = uuid.uuid4()
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tenants (id, name, slug) VALUES (%s, %s, %s)",
                (tenant_id, name, f"test-{tenant_id.hex[:8]}"),
            )
        conn.commit()
    return tenant_id


def test_list_applications_paginates_and_filters_by_tenant_and_search():
    tenant_a = _create_tenant(name="Tenant A")
    tenant_b = _create_tenant(name="Tenant B")

    client = TestClient(app)

    payload_a1 = {
        "tenant_id": str(tenant_a),
        "external_id": "EXT-ALPHA",
        "applicant_data": {"name": "Jane Alpha"},
        "financial_data": {
            "net_monthly_income": 1000,
            "monthly_obligations": 200,
            "existing_loans_payment": 100,
        },
        "loan_request": {"loan_amount": 12000, "estimated_payment": 300},
        "credit_bureau_data": None,
        "source": "web",
    }

    payload_a2 = {
        "tenant_id": str(tenant_a),
        "external_id": "EXT-BETA",
        "applicant_data": {"name": "Jane Beta"},
        "financial_data": {
            "net_monthly_income": 1200,
            "monthly_obligations": 100,
            "existing_loans_payment": 100,
        },
        "loan_request": {"loan_amount": 8000, "estimated_payment": 200},
        "credit_bureau_data": None,
        "source": "web",
    }

    payload_b1 = {
        "tenant_id": str(tenant_b),
        "external_id": "EXT-GAMMA",
        "applicant_data": {"name": "Other Tenant"},
        "financial_data": {
            "net_monthly_income": 1000,
            "monthly_obligations": 200,
            "existing_loans_payment": 100,
        },
        "loan_request": {"loan_amount": 12000, "estimated_payment": 300},
        "credit_bureau_data": None,
        "source": "web",
    }

    for payload in (payload_a1, payload_a2, payload_b1):
        r_create = client.post("/api/v1/applications", json=payload)
        assert r_create.status_code == 201, r_create.text

    # Tenant filter: should only see Tenant A apps.
    r_list = client.get("/api/v1/applications", params={"tenant_id": str(tenant_a)})
    assert r_list.status_code == 200, r_list.text
    data = r_list.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert {item["external_id"] for item in data["items"]} == {"EXT-ALPHA", "EXT-BETA"}

    # Search: by external_id and applicant name.
    r_search_ext = client.get(
        "/api/v1/applications",
        params={"tenant_id": str(tenant_a), "search": "ALPHA"},
    )
    assert r_search_ext.status_code == 200, r_search_ext.text
    assert r_search_ext.json()["total"] == 1
    assert r_search_ext.json()["items"][0]["external_id"] == "EXT-ALPHA"

    r_search_name = client.get(
        "/api/v1/applications",
        params={"tenant_id": str(tenant_a), "search": "beta"},
    )
    assert r_search_name.status_code == 200, r_search_name.text
    assert r_search_name.json()["total"] == 1
    assert r_search_name.json()["items"][0]["external_id"] == "EXT-BETA"

    # Pagination: page_size=1 should return 1 item.
    r_page_1 = client.get(
        "/api/v1/applications",
        params={"tenant_id": str(tenant_a), "page": 1, "page_size": 1},
    )
    assert r_page_1.status_code == 200, r_page_1.text
    assert r_page_1.json()["total"] == 2
    assert len(r_page_1.json()["items"]) == 1

    r_page_2 = client.get(
        "/api/v1/applications",
        params={"tenant_id": str(tenant_a), "page": 2, "page_size": 1},
    )
    assert r_page_2.status_code == 200, r_page_2.text
    assert r_page_2.json()["total"] == 2
    assert len(r_page_2.json()["items"]) == 1
