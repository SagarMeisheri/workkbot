import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from config import settings


@pytest.mark.asyncio
async def test_sovereign_health_endpoint():
    """
    Scorecard Gate B1-G3: Sovereign Region Health Endpoint
    GET /health returns HTTP 200 with JSON payload explicitly validating 'region': 'asia-south1'
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["region"] == "asia-south1"
        assert "timestamp" in data
