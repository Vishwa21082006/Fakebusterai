"""
FakeBuster AI — Auth Endpoint Tests
"""

import pytest


@pytest.mark.asyncio
async def test_register_and_login(client):
    """Full auth flow: register → login → access /me."""
    # Register
    reg_resp = await client.post("/api/v1/auth/register", json={
        "email": "test@fakebuster.ai",
        "password": "Str0ngP@ssw0rd!",
    })
    assert reg_resp.status_code == 201
    user_data = reg_resp.json()
    assert user_data["email"] == "test@fakebuster.ai"
    assert user_data["role"] == "user"

    # Login
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "test@fakebuster.ai",
        "password": "Str0ngP@ssw0rd!",
    })
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data

    # Access /me with the token
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "test@fakebuster.ai"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    """Registration with duplicate email should return 409."""
    await client.post("/api/v1/auth/register", json={
        "email": "dupe@fakebuster.ai",
        "password": "Str0ngP@ssw0rd!",
    })
    resp = await client.post("/api/v1/auth/register", json={
        "email": "dupe@fakebuster.ai",
        "password": "AnotherP@ss123",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    """Login with wrong password should return 401."""
    await client.post("/api/v1/auth/register", json={
        "email": "wrong@fakebuster.ai",
        "password": "Str0ngP@ssw0rd!",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "wrong@fakebuster.ai",
        "password": "WrongPassword123",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_without_token(client):
    """Accessing /me without token should return 401."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
