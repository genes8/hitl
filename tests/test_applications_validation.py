import uuid

from fastapi.testclient import TestClient

from src.main import app


def test_create_application_missing_required_sections_returns_422():
    client = TestClient(app)

    payload = {
        "external_id": "APP-1",
        "tenant_id": str(uuid.uuid4()),
        "applicant_data": {"personal": {}},
        "financial_data": {"income": {}},
        "loan_request": {"amount": 1000},
    }

    r = client.post("/api/v1/applications", json=payload)
    assert r.status_code == 422
