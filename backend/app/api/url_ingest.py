"""
FakeBuster AI — URL Ingestion Endpoint
Downloads media from a public URL with comprehensive validation:
  • Domain validation
  • HTTP status checks (404, 403)
  • Content-Type & Content-Length validation
  • Timeout handling
  • ClamAV scanning
"""

import asyncio
import logging
import tempfile
import shutil
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import (
    APIRouter, Depends, HTTPException, BackgroundTasks, status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.analysis import Analysis
from app.schemas.analysis import AnalysisResponse, URLIngestRequest
from app.core.security import get_current_user
from app.core.rate_limiter import RateLimiter
from app.core.exceptions import URLIngestionError
from app.services.media_service import (
    ALLOWED_MIMES, validate_mime_type, validate_file_size,
    compute_file_hash, scan_for_viruses, cleanup_file,
)
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/ingest", tags=["URL Ingestion"])

# Blocked domains (private/internal networks)
BLOCKED_DOMAINS = {
    "localhost", "127.0.0.1", "0.0.0.0", "::1",
    "169.254.169.254",  # AWS metadata endpoint — SSRF prevention
    "metadata.google.internal",  # GCP metadata endpoint
}

DOWNLOAD_TIMEOUT = 15.0  # seconds


def _validate_url(url: str) -> None:
    """Validate URL scheme, domain, and block internal addresses."""
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise URLIngestionError(
            "Only HTTP and HTTPS URLs are supported",
            detail={"scheme": parsed.scheme},
        )

    hostname = parsed.hostname or ""
    if hostname in BLOCKED_DOMAINS:
        raise URLIngestionError(
            f"Domain '{hostname}' is not allowed",
            detail={"hostname": hostname},
        )

    # Block private IP ranges
    if hostname.startswith(("10.", "172.", "192.168.")):
        raise URLIngestionError(
            "Private/internal URLs are not allowed",
            detail={"hostname": hostname},
        )


@router.post(
    "/url",
    response_model=AnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(RateLimiter(max_requests=10, window_seconds=60))],
)
async def ingest_url(
    body: URLIngestRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Ingest media from a public URL for deepfake analysis.

    ── Validation Pipeline ──
    1. Domain validation (block private/internal)
    2. HEAD request → check HTTP status, Content-Type, Content-Length
    3. Download to temp file with timeout
    4. Re-validate MIME type on actual content
    5. ClamAV scan
    6. Move to permanent storage
    7. Create Analysis record → dispatch background detection
    """
    url = str(body.url)
    saved_path = None

    try:
        # 1. Validate URL
        _validate_url(url)

        async with httpx.AsyncClient(
            timeout=DOWNLOAD_TIMEOUT,
            follow_redirects=True,
            max_redirects=5,
        ) as client:

            # 2. HEAD request — check accessibility and content info
            try:
                head_resp = await client.head(url)
            except httpx.TimeoutException:
                raise URLIngestionError(
                    f"URL timed out after {DOWNLOAD_TIMEOUT}s",
                    detail={"url": url, "timeout": DOWNLOAD_TIMEOUT},
                )
            except httpx.RequestError as e:
                raise URLIngestionError(
                    f"Failed to reach URL: {str(e)}",
                    detail={"url": url},
                )

            # Check HTTP status
            if head_resp.status_code == 404:
                raise URLIngestionError(
                    "URL returned 404 — resource not found",
                    detail={"url": url, "status": 404},
                )
            elif head_resp.status_code == 403:
                raise URLIngestionError(
                    "URL returned 403 — access denied. Ensure the resource is publicly accessible.",
                    detail={"url": url, "status": 403},
                )
            elif head_resp.status_code >= 400:
                raise URLIngestionError(
                    f"URL returned HTTP {head_resp.status_code}",
                    detail={"url": url, "status": head_resp.status_code},
                )

            # Check Content-Type from HEAD
            content_type = head_resp.headers.get("content-type", "").split(";")[0].strip()
            if content_type and content_type not in ALLOWED_MIMES:
                raise URLIngestionError(
                    f"Unsupported content type from URL: {content_type}",
                    detail={"content_type": content_type, "allowed": sorted(ALLOWED_MIMES)},
                )

            # Check Content-Length from HEAD
            content_length = head_resp.headers.get("content-length")
            if content_length:
                try:
                    size = int(content_length)
                    validate_file_size(size)
                except ValueError:
                    pass

            # 3. Download the file
            try:
                get_resp = await client.get(url)
                get_resp.raise_for_status()
            except httpx.TimeoutException:
                raise URLIngestionError(
                    f"Download timed out after {DOWNLOAD_TIMEOUT}s",
                    detail={"url": url},
                )
            except httpx.HTTPStatusError as e:
                raise URLIngestionError(
                    f"Download failed with HTTP {e.response.status_code}",
                    detail={"url": url, "status": e.response.status_code},
                )

            content = get_resp.content
            validate_file_size(len(content))

            # 4. Determine actual MIME type
            actual_ct = get_resp.headers.get("content-type", "").split(";")[0].strip()
            if actual_ct:
                media_type = validate_mime_type(actual_ct)
            elif content_type:
                media_type = validate_mime_type(content_type)
            else:
                raise URLIngestionError(
                    "Could not determine content type of the URL resource",
                    detail={"url": url},
                )

            # Save to storage
            import uuid
            storage_dir = Path(settings.MEDIA_STORAGE_PATH)
            storage_dir.mkdir(parents=True, exist_ok=True)

            ext_map = {
                "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
                "video/mp4": ".mp4", "video/webm": ".webm",
            }
            ext = ext_map.get(actual_ct or content_type, ".bin")
            unique_name = f"{uuid.uuid4().hex}{ext}"
            saved_path = str(storage_dir / unique_name)

            with open(saved_path, "wb") as f:
                f.write(content)

        # 5. ClamAV scan
        scan_for_viruses(saved_path)

        # 6. Compute hash
        file_hash = compute_file_hash(saved_path)

        # 7. Create Analysis record
        analysis = Analysis(
            user_id=current_user.id,
            source_type="url",
            source_ref=saved_path,
            media_type=media_type,
            status="queued",
            file_hash=file_hash,
        )
        db.add(analysis)
        await db.flush()
        await db.refresh(analysis)

        # 8. Dispatch background task
        from app.tasks.analysis_tasks import run_analysis
        background_tasks.add_task(run_analysis, str(analysis.id))

        logger.info(
            f"URL ingestion accepted: analysis={analysis.id} url={url} "
            f"type={media_type} hash={file_hash[:16]}..."
        )

        return AnalysisResponse(
            id=str(analysis.id),
            source_type=analysis.source_type,
            media_type=analysis.media_type,
            status=analysis.status,
            file_hash=analysis.file_hash,
            created_at=analysis.created_at.isoformat(),
        )

    except (URLIngestionError, HTTPException):
        if saved_path:
            cleanup_file(saved_path)
        raise
    except Exception as e:
        if saved_path:
            cleanup_file(saved_path)
        logger.error(f"URL ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"URL ingestion failed: {str(e)}",
        )
