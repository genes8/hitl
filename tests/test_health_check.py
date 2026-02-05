import pytest

from tests._client import get_async_client


@pytest.mark.anyio
async def test_health_check():
    async with get_async_client() as client:
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
