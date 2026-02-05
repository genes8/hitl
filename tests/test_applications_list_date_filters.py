import os
import uuid
from datetime import datetime, timedelta, timezone

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


def test_list_applications_filters_by_from_date_and_to_date():
    tenant_id = _create_tenant()
    client = TestClient(app)

    older_id = _create_application(client, tenant_id=tenant_id, applicant_name="Old")
    newer_id = _create_application(client, tenant_id=tenant_id, applicant_name="New")

    now = datetime.now(timezone.utc)

    # Make one application appear "old" by moving created_at back.
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE applications SET created_at = %s WHERE id = %s",
                (now - timedelta(days=10), older_id),
            )
            cur.execute(
                "UPDATE applications SET created_at = %s WHERE id = %s",
                (now - timedelta(hours=1), newer_id),
            )
        conn.commit()

    from_date = (now - timedelta(days=2)).isoformat()

    r = client.get(f"/api/v1/applications?tenant_id={tenant_id}&from_date={from_date}")
    assert r.status_code == 200, r.text

    data = r.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == newer_id

    to_date = (now - timedelta(days=5)).isoformat()
    r2 = client.get(f"/api/v1/applications?tenant_id={tenant_id}&to_date={to_date}")
    assert r2.status_code == 200, r2.text

    data2 = r2.json()
    assert data2["total"] == 1
    assert len(data2["items"]) == 1
    assert data2["items"][0]["id"] == older_id
