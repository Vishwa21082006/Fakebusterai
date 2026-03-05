"""
FakeBuster AI — URL Ingestion Tests
"""

import pytest


@pytest.mark.asyncio
async def test_ingest_url_without_auth(client):
    """URL ingestion without auth should return 401."""
    resp = await client.post(
        "/api/v1/ingest/url",
        json={"url": "https://example.com/image.jpg"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ingest_blocked_domain(client):
    """URL from blocked domain should be rejected."""
    # Register and login
    await client.post("/api/v1/auth/register", json={
        "email": "urltester@fakebuster.ai",
        "password": "Str0ngP@ssw0rd!",
    })
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "urltester@fakebuster.ai",
        "password": "Str0ngP@ssw0rd!",
    })
    token = login_resp.json()["access_token"]

    resp = await client.post(
        "/api/v1/ingest/url",
        headers={"Authorization": f"Bearer {token}"},
        json={"url": "http://169.254.169.254/latest/meta-data/"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ingest_invalid_url(client):
    """Invalid URL format should be rejected by Pydantic."""
    await client.post("/api/v1/auth/register", json={
        "email": "urltester2@fakebuster.ai",
        "password": "Str0ngP@ssw0rd!",
    })
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "urltester2@fakebuster.ai",
        "password": "Str0ngP@ssw0rd!",
    })
    token = login_resp.json()["access_token"]

    resp = await client.post(
        "/api/v1/ingest/url",
        headers={"Authorization": f"Bearer {token}"},
        json={"url": "not-a-url"},
    )
    assert resp.status_code == 422
