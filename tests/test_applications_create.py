import uuid
import pytest

from tests._client import get_async_client


@pytest.mark.anyio
async def test_create_application_201_and_derives_ratios():
    payload = {
        "tenant_id": str(uuid.uuid4()),
        "applicant_data": {"personal": {}, "address": {}, "employment": {}},
        "financial_data": {
            "net_monthly_income": 1000,
            "monthly_obligations": 100,
            "existing_loans_payment": 50,
        },
        "loan_request": {
            "loan_amount": 12000,
            "estimated_payment": 200,
        },
    }

    async with get_async_client() as client:
        r = await client.post("/api/v1/applications", json=payload)
        assert r.status_code == 201
        data = r.json()
        assert data["meta"]["derived"]["dti_ratio"] is not None
