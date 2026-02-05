import os
import uuid

import psycopg
from fastapi.testclient import TestClient
from psycopg.types.json import Json

from src.main import app


def _sync_dsn() -> str:
    dsn = os.environ.get("DATABASE_URL")
    assert dsn, "DATABASE_URL must be set in CI"
    return dsn.replace("postgresql+asyncpg://", "postgresql://")


def _create_tenant(*, name: str) -> uuid.UUID:
    tenant_id = uuid.uuid4()
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tenants (id, name, slug) VALUES (%s, %s, %s)",
                (tenant_id, name, f"test-{tenant_id.hex[:8]}"),
            )
        conn.commit()
    return tenant_id


def _create_application(*, tenant_id: uuid.UUID) -> str:
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
    return r.json()["id"]


def _insert_scoring_result(*, application_id: str) -> uuid.UUID:
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
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    scoring_id,
                    uuid.UUID(application_id),
                    "demo-model",
                    "1",
                    720,
                    0.1234,
                    "medium",
                    "human_review",
                    None,
                    Json({"f1": 1}),
                    Json({"f1": 0.01}),
                    Json({"top": ["f1"]}),
                    42,
                ),
            )
        conn.commit()

    return scoring_id


def test_get_application_200():
    tenant_id = _create_tenant(name="Tenant A")
    application_id = _create_application(tenant_id=tenant_id)

    client = TestClient(app)

    r = client.get(f"/api/v1/applications/{application_id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == application_id
    assert body.get("scoring_result") is None


def test_get_application_404_on_wrong_tenant_scope():
    tenant_a = _create_tenant(name="Tenant A")
    tenant_b = _create_tenant(name="Tenant B")
    application_id = _create_application(tenant_id=tenant_a)

    client = TestClient(app)

    r = client.get(f"/api/v1/applications/{application_id}", params={"tenant_id": str(tenant_b)})
    assert r.status_code == 404, r.text


def test_get_application_includes_scoring_result_if_exists():
    tenant_id = _create_tenant(name="Tenant A")
    application_id = _create_application(tenant_id=tenant_id)
    scoring_id = _insert_scoring_result(application_id=application_id)

    client = TestClient(app)

    r = client.get(f"/api/v1/applications/{application_id}")
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["id"] == application_id
    assert body.get("scoring_result") is not None
    assert body["scoring_result"]["id"] == str(scoring_id)
    assert body["scoring_result"]["application_id"] == application_id


def _insert_queue_entry(*, application_id: str) -> uuid.UUID:
    queue_id = uuid.uuid4()

    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO analyst_queues (
                    id,
                    application_id,
                    analyst_id,
                    priority,
                    priority_reason,
                    status,
                    sla_deadline,
                    sla_breached,
                    routing_reason,
                    score_at_routing
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, now() + interval '8 hours', %s, %s, %s
                )
                """,
                (
                    queue_id,
                    uuid.UUID(application_id),
                    None,
                    10,
                    "test",
                    "pending",
                    False,
                    "borderline_score",
                    650,
                ),
            )
        conn.commit()

    return queue_id


def _insert_decision(*, application_id: str) -> uuid.UUID:
    decision_id = uuid.uuid4()

    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO decisions (
                    id,
                    application_id,
                    scoring_result_id,
                    analyst_id,
                    decision_type,
                    decision_outcome,
                    approved_terms,
                    conditions,
                    reasoning,
                    reasoning_category,
                    override_flag,
                    created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now()
                )
                """,
                (
                    decision_id,
                    uuid.UUID(application_id),
                    None,
                    None,
                    "analyst_approve",
                    "approved",
                    Json({"amount": 1000}),
                    Json([]),
                    "ok",
                    "standard",
                    False,
                ),
            )
        conn.commit()

    return decision_id


def test_get_application_includes_queue_and_decisions_if_exist():
    tenant_id = _create_tenant(name="Tenant A")
    application_id = _create_application(tenant_id=tenant_id)

    queue_id = _insert_queue_entry(application_id=application_id)
    decision_id = _insert_decision(application_id=application_id)

    client = TestClient(app)

    r = client.get(f"/api/v1/applications/{application_id}")
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["queue_entry"] is not None
    assert body["queue_entry"]["id"] == str(queue_id)

    assert isinstance(body["decision_history"], list)
    assert body["decision_history"][0]["id"] == str(decision_id)
