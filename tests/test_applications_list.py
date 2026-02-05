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


def test_list_applications_filters_by_date_range_and_sorts_by_score():
    tenant_id = _create_tenant(name="Tenant Dates")
    client = TestClient(app)

    payloads = [
        {
            "tenant_id": str(tenant_id),
            "external_id": "EXT-OLD",
            "applicant_data": {"name": "Old"},
            "financial_data": {
                "net_monthly_income": 1000,
                "monthly_obligations": 200,
                "existing_loans_payment": 100,
            },
            "loan_request": {"loan_amount": 1000, "estimated_payment": 50},
            "credit_bureau_data": None,
            "source": "web",
        },
        {
            "tenant_id": str(tenant_id),
            "external_id": "EXT-NEW",
            "applicant_data": {"name": "New"},
            "financial_data": {
                "net_monthly_income": 1000,
                "monthly_obligations": 200,
                "existing_loans_payment": 100,
            },
            "loan_request": {"loan_amount": 2000, "estimated_payment": 100},
            "credit_bureau_data": None,
            "source": "web",
        },
        {
            "tenant_id": str(tenant_id),
            "external_id": "EXT-NOSCORE",
            "applicant_data": {"name": "NoScore"},
            "financial_data": {
                "net_monthly_income": 1000,
                "monthly_obligations": 200,
                "existing_loans_payment": 100,
            },
            "loan_request": {"loan_amount": 3000, "estimated_payment": 150},
            "credit_bureau_data": None,
            "source": "web",
        },
    ]

    app_ids: dict[str, str] = {}
    for p in payloads:
        r = client.post("/api/v1/applications", json=p)
        assert r.status_code == 201, r.text
        app_ids[p["external_id"]] = r.json()["id"]

    # Force deterministic created_at values.
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE applications SET created_at = %s WHERE id = %s",
                ("2026-01-01T00:00:00+00:00", app_ids["EXT-OLD"]),
            )
            cur.execute(
                "UPDATE applications SET created_at = %s WHERE id = %s",
                ("2026-01-10T00:00:00+00:00", app_ids["EXT-NEW"]),
            )
            cur.execute(
                "UPDATE applications SET created_at = %s WHERE id = %s",
                ("2026-01-10T00:00:00+00:00", app_ids["EXT-NOSCORE"]),
            )

            # Add scoring results for two of them.
            cur.execute(
                """
                INSERT INTO scoring_results (
                    id,
                    application_id,
                    model_id,
                    model_version,
                    score,
                    probability_default,
                    risk_category,
                    routing_decision,
                    threshold_config_id,
                    features,
                    shap_values,
                    top_factors,
                    scoring_time_ms
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s)
                """,
                (
                    uuid.uuid4(),
                    app_ids["EXT-OLD"],
                    "demo",
                    "v1",
                    700,
                    0.1234,
                    "low",
                    "auto_approve",
                    None,
                    "{}",
                    "{}",
                    "{}",
                    5,
                ),
            )
            cur.execute(
                """
                INSERT INTO scoring_results (
                    id,
                    application_id,
                    model_id,
                    model_version,
                    score,
                    probability_default,
                    risk_category,
                    routing_decision,
                    threshold_config_id,
                    features,
                    shap_values,
                    top_factors,
                    scoring_time_ms
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s)
                """,
                (
                    uuid.uuid4(),
                    app_ids["EXT-NEW"],
                    "demo",
                    "v1",
                    500,
                    0.2345,
                    "medium",
                    "human_review",
                    None,
                    "{}",
                    "{}",
                    "{}",
                    5,
                ),
            )
        conn.commit()

    # Date filter should exclude EXT-OLD.
    r_range = client.get(
        "/api/v1/applications",
        params={
            "tenant_id": str(tenant_id),
            "from_date": "2026-01-05T00:00:00Z",
            "to_date": "2026-01-31T00:00:00Z",
        },
    )
    assert r_range.status_code == 200, r_range.text
    assert {i["external_id"] for i in r_range.json()["items"]} == {"EXT-NEW", "EXT-NOSCORE"}

    # Sort by score ascending: scored apps first (500, 700), null scores last.
    r_sort = client.get(
        "/api/v1/applications",
        params={
            "tenant_id": str(tenant_id),
            "sort_by": "score",
            "sort_order": "asc",
        },
    )
    assert r_sort.status_code == 200, r_sort.text
    items = r_sort.json()["items"]
    assert items[0]["external_id"] == "EXT-NEW"
    assert items[1]["external_id"] == "EXT-OLD"
    assert items[-1]["external_id"] == "EXT-NOSCORE"
