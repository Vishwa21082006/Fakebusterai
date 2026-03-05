"""
FakeBuster AI — Health Endpoint Tests
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Health check should return 200 with service status."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "db" in data
    assert "redis" in data
    assert "clamav" in data


@pytest.mark.asyncio
async def test_ready_endpoint(client):
    """Readiness probe should return 200 when services are up."""
    response = await client.get("/api/v1/ready")
    assert response.status_code == 200
    data = response.json()
    assert "ready" in data
