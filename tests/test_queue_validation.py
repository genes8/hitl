from fastapi.testclient import TestClient

from src.main import app


def test_queue_list_invalid_tenant_id_422():
    client = TestClient(app)
    r = client.get("/api/v1/queue", params={"tenant_id": "not-a-uuid"})
    assert r.status_code == 422


def test_queue_summary_invalid_tenant_id_422():
    client = TestClient(app)
    r = client.get("/api/v1/queue/summary", params={"tenant_id": "not-a-uuid"})
    assert r.status_code == 422
