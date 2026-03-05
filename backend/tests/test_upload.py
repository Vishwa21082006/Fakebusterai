"""
FakeBuster AI — Upload Endpoint Tests
"""

import io
import pytest
from unittest.mock import patch, MagicMock


async def _get_auth_token(client) -> str:
    """Helper: register + login, return JWT token."""
    await client.post("/api/v1/auth/register", json={
        "email": "uploader@fakebuster.ai",
        "password": "Str0ngP@ssw0rd!",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "uploader@fakebuster.ai",
        "password": "Str0ngP@ssw0rd!",
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_upload_valid_image(client, tmp_path):
    """Upload a valid JPEG image should return 202."""
    token = await _get_auth_token(client)

    # Create a small fake JPEG file (JPEG magic bytes)
    fake_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 100

    with patch("app.services.media_service.scan_for_viruses"):
        with patch("app.services.media_service.save_upload", return_value=(str(tmp_path / "test.jpg"), ".jpg")):
            with patch("app.services.media_service.compute_file_hash", return_value="abc123"):
                with patch("app.tasks.analysis_tasks.run_analysis"):
                    resp = await client.post(
                        "/api/v1/upload",
                        headers={"Authorization": f"Bearer {token}"},
                        files={"file": ("test.jpg", io.BytesIO(fake_jpeg), "image/jpeg")},
                    )

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "queued"
    assert data["media_type"] == "image"


@pytest.mark.asyncio
async def test_upload_invalid_mime(client):
    """Upload with invalid MIME type should be rejected."""
    token = await _get_auth_token(client)

    resp = await client.post(
        "/api/v1/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("malware.exe", io.BytesIO(b"\x00" * 100), "application/x-executable")},
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_without_auth(client):
    """Upload without auth should return 401."""
    resp = await client.post(
        "/api/v1/upload",
        files={"file": ("test.jpg", io.BytesIO(b"\x00" * 100), "image/jpeg")},
    )
    assert resp.status_code == 401
