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

    assert data["queue_info"] is None
    assert data["decision_history"] == []


def _insert_scoring_result(application_id: str):
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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s)
                """,
                (
                    scoring_id,
                    uuid.UUID(application_id),
                    "test-model",
                    "v1",
                    720,
                    0.1234,
                    "low",
                    "auto_approve",
                    None,
                    "{}",
                    "{}",
                    '{"top": ["income"]}',
                    15,
                ),
            )
        conn.commit()

    return scoring_id


def _insert_queue_entry(application_id: str):
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
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW() + INTERVAL '8 hours', %s, %s, %s)
                """,
                (
                    queue_id,
                    uuid.UUID(application_id),
                    None,
                    10,
                    "high_value_loan",
                    "pending",
                    False,
                    "borderline_score",
                    650,
                ),
            )
        conn.commit()

    return queue_id


def _insert_decision(application_id: str, *, decision_type: str = "analyst_approve", decision_outcome: str = "approved"):
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
                    review_time_seconds
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s)
                """,
                (
                    decision_id,
                    uuid.UUID(application_id),
                    None,
                    None,
                    decision_type,
                    decision_outcome,
                    '{"apr": 0.12}',
                    "[]",
                    "ok",
                    "policy",
                    False,
                    42,
                ),
            )
        conn.commit()

    return decision_id


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


def test_get_application_includes_scoring_result_when_present():
    tenant_id = _create_tenant()
    created = _create_application(tenant_id)

    _insert_scoring_result(created["id"])

    client = TestClient(app)
    r = client.get(f"/api/v1/applications/{created['id']}")

    assert r.status_code == 200, r.text
    data = r.json()

    assert data["scoring_result"] is not None
    assert data["scoring_result"]["application_id"] == created["id"]
    assert data["scoring_result"]["model_id"] == "test-model"


def test_get_application_includes_queue_info_when_present():
    tenant_id = _create_tenant()
    created = _create_application(tenant_id)

    _insert_queue_entry(created["id"])

    client = TestClient(app)
    r = client.get(f"/api/v1/applications/{created['id']}")

    assert r.status_code == 200, r.text
    data = r.json()

    assert data["queue_info"] is not None
    assert data["queue_info"]["application_id"] == created["id"]
    assert data["queue_info"]["status"] == "pending"


def test_get_application_includes_decision_history_when_present():
    tenant_id = _create_tenant()
    created = _create_application(tenant_id)

    _insert_decision(created["id"], decision_type="analyst_approve", decision_outcome="approved")
    _insert_decision(created["id"], decision_type="analyst_decline", decision_outcome="declined")

    client = TestClient(app)
    r = client.get(f"/api/v1/applications/{created['id']}")

    assert r.status_code == 200, r.text
    data = r.json()

    assert len(data["decision_history"]) == 2
    assert data["decision_history"][0]["application_id"] == created["id"]
    assert data["decision_history"][0]["decision_type"] in {"analyst_approve", "analyst_decline"}
