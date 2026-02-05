import uuid
import pytest

from tests._client import get_async_client


@pytest.mark.anyio
async def test_create_application_missing_required_sections_returns_422():
    payload = {
        "external_id": "APP-1",
        "tenant_id": str(uuid.uuid4()),
        "applicant_data": {"personal": {}},
        "financial_data": {"income": {}},
        "loan_request": {"amount": 1000},
    }

    async with get_async_client() as client:
        r = await client.post("/api/v1/applications", json=payload)
        # Depending on our handler, this should be 422.
        assert r.status_code == 422
