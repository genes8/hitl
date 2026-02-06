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
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    scoring_id,
                    application_id,
                    "xgb",
                    "v0",
                    720,
                    0.1234,
                    "low",
                    "auto_approve",
                    None,
                    {"dti_ratio": 0.3},
                    {"dti_ratio": 0.01},
                    {"top": ["dti_ratio"]},
                    42,
                ),
            )
        conn.commit()
    return scoring_id


def _insert_queue_entry(*, application_id: uuid.UUID) -> uuid.UUID:
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
                  assigned_at,
                  started_at,
                  completed_at,
                  sla_deadline,
                  sla_breached,
                  routing_reason,
                  score_at_routing
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    queue_id,
                    application_id,
                    None,
                    10,
                    "borderline_score",
                    "pending",
                    None,
                    None,
                    None,
                    "2030-01-01T00:00:00+00:00",
                    False,
                    "borderline_score",
                    650,
                ),
            )
        conn.commit()
    return queue_id


def _insert_decision(*, application_id: uuid.UUID) -> uuid.UUID:
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
                  override_direction,
                  override_justification,
                  override_approved_by,
                  override_approved_at,
                  review_time_seconds
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    decision_id,
                    application_id,
                    None,
                    None,
                    "analyst_approve",
                    "approved",
                    {"apr": 12.5},
                    None,
                    "looks good",
                    "income",
                    False,
                    None,
                    None,
                    None,
                    None,
                    120,
                ),
            )
        conn.commit()
    return decision_id


def test_get_application_200_after_create():
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
        "loan_request": {"loan_amount": 12000, "estimated_payment": 300},
        "credit_bureau_data": None,
        "source": "web",
    }

    created = client.post("/api/v1/applications", json=payload)
    assert created.status_code == 201, created.text

    app_id = created.json()["id"]

    r = client.get(f"/api/v1/applications/{app_id}")
    assert r.status_code == 200, r.text
    assert r.json()["id"] == app_id
    assert r.json()["tenant_id"] == str(tenant_id)
    assert r.json()["scoring_result"] is None
    assert r.json()["queue_info"] is None
    assert r.json()["decision_history"] == []


def test_get_application_includes_scoring_result_when_exists():
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
        "loan_request": {"loan_amount": 12000, "estimated_payment": 300},
        "credit_bureau_data": None,
        "source": "web",
    }

    created = client.post("/api/v1/applications", json=payload)
    assert created.status_code == 201, created.text

    app_id = uuid.UUID(created.json()["id"])
    scoring_id = _insert_scoring_result(application_id=app_id)

    r = client.get(f"/api/v1/applications/{app_id}")
    assert r.status_code == 200, r.text

    scoring = r.json()["scoring_result"]
    assert scoring is not None
    assert scoring["id"] == str(scoring_id)
    assert scoring["application_id"] == str(app_id)
    assert scoring["score"] == 720
    assert scoring["risk_category"] == "low"

    assert r.json()["decision_history"] == []


def test_get_application_includes_queue_info_when_exists():
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
        "loan_request": {"loan_amount": 12000, "estimated_payment": 300},
        "credit_bureau_data": None,
        "source": "web",
    }

    created = client.post("/api/v1/applications", json=payload)
    assert created.status_code == 201, created.text

    app_id = uuid.UUID(created.json()["id"])
    queue_id = _insert_queue_entry(application_id=app_id)

    r = client.get(f"/api/v1/applications/{app_id}")
    assert r.status_code == 200, r.text

    queue_info = r.json()["queue_info"]
    assert queue_info is not None
    assert queue_info["id"] == str(queue_id)
    assert queue_info["application_id"] == str(app_id)
    assert queue_info["status"] == "pending"
    assert queue_info["priority"] == 10
    assert queue_info["routing_reason"] == "borderline_score"
    assert queue_info["score_at_routing"] == 650

    assert r.json()["decision_history"] == []


def test_get_application_includes_decision_history_when_exists():
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
        "loan_request": {"loan_amount": 12000, "estimated_payment": 300},
        "credit_bureau_data": None,
        "source": "web",
    }

    created = client.post("/api/v1/applications", json=payload)
    assert created.status_code == 201, created.text

    app_id = uuid.UUID(created.json()["id"])
    decision_id = _insert_decision(application_id=app_id)

    r = client.get(f"/api/v1/applications/{app_id}")
    assert r.status_code == 200, r.text

    decisions = r.json()["decision_history"]
    assert isinstance(decisions, list)
    assert len(decisions) == 1
    assert decisions[0]["id"] == str(decision_id)
    assert decisions[0]["application_id"] == str(app_id)
    assert decisions[0]["decision_type"] == "analyst_approve"
    assert decisions[0]["decision_outcome"] == "approved"


def test_get_application_404_when_unknown_uuid():
    client = TestClient(app)
    unknown = uuid.uuid4()

    r = client.get(f"/api/v1/applications/{unknown}")
    assert r.status_code == 404


def test_get_application_404_when_tenant_mismatch():
    tenant_id = _create_tenant()
    other_tenant_id = _create_tenant()
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
        "loan_request": {"loan_amount": 12000, "estimated_payment": 300},
        "credit_bureau_data": None,
        "source": "web",
    }

    created = client.post("/api/v1/applications", json=payload)
    assert created.status_code == 201, created.text

    app_id = created.json()["id"]

    r = client.get(f"/api/v1/applications/{app_id}?tenant_id={other_tenant_id}")
    assert r.status_code == 404


def test_get_application_422_when_bad_tenant_id_format():
    client = TestClient(app)

    r = client.get(f"/api/v1/applications/{uuid.uuid4()}?tenant_id=not-a-uuid")
    assert r.status_code == 422


def test_get_application_404_when_bad_id_format():
    client = TestClient(app)

    r = client.get("/api/v1/applications/not-a-uuid")
    assert r.status_code == 404
