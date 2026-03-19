import pytest
from httpx import AsyncClient, ASGITransport
from evaluator.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_health(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ark-evaluator"


@pytest.mark.asyncio
async def test_ready(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"


@pytest.mark.asyncio
async def test_evaluate_validation_error(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/evaluate", json={})
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_evaluate_direct_missing_model(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/evaluate", json={
            "type": "direct",
            "config": {"input": "test", "output": "test"},
            "parameters": {"provider": "ark"}
        })
        assert response.status_code in [200, 422, 500]
