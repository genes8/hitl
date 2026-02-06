from fastapi.testclient import TestClient

from src.main import app


def test_error_responses_include_request_id_in_body_and_header():
    client = TestClient(app)

    r = client.get("/this-route-does-not-exist")
    assert r.status_code == 404

    payload = r.json()
    assert "request_id" in payload
    assert payload["request_id"], payload

    assert r.headers.get("x-request-id") == payload["request_id"]
