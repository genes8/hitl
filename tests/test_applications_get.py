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


def _insert_scoring_result(*, application_id: uuid.UUID) -> uuid.UUID:
    scoring_id = uuid.uuid4()
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
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
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    scoring_id,
                    application_id,
                    "test-model",
                    "v1",
                    720,
                    0.1234,
                    "low",
                    "auto_approve",
                    None,
                    {"f": 1},
                    {"s": [0.1, 0.2]},
                    {"factors": ["income"]},
                    42,
                ),
            )
        conn.commit()
    return scoring_id


def test_get_application_200():
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
        "loan_request": {
            "loan_amount": 12000,
            "estimated_payment": 300,
        },
        "credit_bureau_data": None,
        "source": "web",
    }

    r_create = client.post("/api/v1/applications", json=payload)
    assert r_create.status_code == 201, r_create.text
    app_id = r_create.json()["id"]

    _insert_scoring_result(application_id=uuid.UUID(app_id))

    r_get = client.get(f"/api/v1/applications/{app_id}")
    assert r_get.status_code == 200, r_get.text
    body = r_get.json()
    assert body["id"] == app_id
    assert body["scoring_result"] is not None
    assert body["scoring_result"]["application_id"] == app_id
    assert body["scoring_result"]["score"] == 720


def test_get_application_404_when_tenant_scope_mismatch():
    tenant_id = _create_tenant(name="Tenant A")
    other_tenant_id = _create_tenant(name="Tenant B")

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

    r_create = client.post("/api/v1/applications", json=payload)
    assert r_create.status_code == 201, r_create.text
    app_id = r_create.json()["id"]

    r_get = client.get(f"/api/v1/applications/{app_id}", params={"tenant_id": str(other_tenant_id)})
    assert r_get.status_code == 404, r_get.text


def test_get_application_404_when_unknown_id():
    tenant_id = _create_tenant()

    client = TestClient(app)

    unknown_id = uuid.uuid4()
    r_get = client.get(f"/api/v1/applications/{unknown_id}", params={"tenant_id": str(tenant_id)})
    assert r_get.status_code == 404, r_get.text
