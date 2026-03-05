"""
FakeBuster AI — File Upload Endpoint
Handles multipart file upload with MIME validation, size checks,
ClamAV scanning, and background analysis dispatch.
"""

import logging

from fastapi import (
    APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks, status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.analysis import Analysis
from app.schemas.analysis import AnalysisResponse
from app.core.security import get_current_user
from app.core.rate_limiter import RateLimiter
from app.core.exceptions import MediaValidationError, VirusScanError
from app.services.media_service import (
    validate_mime_type, validate_file_size, save_upload,
    compute_file_hash, scan_for_viruses, cleanup_file,
)
from app.tasks.analysis_tasks import run_analysis

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Upload"])


@router.post(
    "/upload",
    response_model=AnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(RateLimiter(max_requests=10, window_seconds=60))],
)
async def upload_media(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload an image or video for deepfake analysis.

    ── Pipeline ──
    1. Validate MIME type (image/jpeg, image/png, video/mp4, etc.)
    2. Validate file size (≤50 MB by default)
    3. Save to disk with UUID name
    4. Compute SHA-256 hash
    5. Scan with ClamAV
    6. Create Analysis record (status=queued)
    7. Dispatch background detection task
    8. Return 202 Accepted with analysis ID
    """
    saved_path = None

    try:
        # 1. Validate MIME type
        content_type = file.content_type or "application/octet-stream"
        media_type = validate_mime_type(content_type)

        # 2. Read file content and validate size
        content = await file.read()
        validate_file_size(len(content))

        # 3. Save to disk
        await file.seek(0)
        saved_path, ext = save_upload(file.file, file.filename)

        # 4. Compute SHA-256 hash
        file_hash = compute_file_hash(saved_path)

        # 5. Scan with ClamAV
        scan_for_viruses(saved_path)

        # 6. Create Analysis record
        analysis = Analysis(
            user_id=current_user.id,
            source_type="upload",
            source_ref=saved_path,
            media_type=media_type,
            status="queued",
            file_hash=file_hash,
        )
        db.add(analysis)
        await db.flush()
        await db.refresh(analysis)

        # 7. Dispatch background task
        background_tasks.add_task(run_analysis, str(analysis.id))

        logger.info(
            f"Upload accepted: analysis={analysis.id} "
            f"user={current_user.email} type={media_type} hash={file_hash[:16]}..."
        )

        # 8. Return response
        return AnalysisResponse(
            id=str(analysis.id),
            source_type=analysis.source_type,
            media_type=analysis.media_type,
            status=analysis.status,
            file_hash=analysis.file_hash,
            created_at=analysis.created_at.isoformat(),
        )

    except (MediaValidationError, VirusScanError):
        if saved_path:
            cleanup_file(saved_path)
        raise
    except HTTPException:
        if saved_path:
            cleanup_file(saved_path)
        raise
    except Exception as e:
        if saved_path:
            cleanup_file(saved_path)
        logger.error(f"Upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload processing failed",
        )


