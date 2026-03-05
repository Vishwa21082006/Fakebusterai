"""
FakeBuster AI — Media Service
Handles file validation, storage, and hashing for uploaded/ingested media.
"""

import hashlib
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from app.config import get_settings
from app.core.exceptions import MediaValidationError
from app.core.virus_scanner import virus_scanner, ScanStatus

settings = get_settings()

# Allowed MIME types for media uploads
ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEO_MIMES = {"video/mp4", "video/webm", "video/avi", "video/quicktime"}
ALLOWED_MIMES = ALLOWED_IMAGE_MIMES | ALLOWED_VIDEO_MIMES


def validate_mime_type(content_type: str) -> str:
    """
    Validate MIME type and return the media category ('image' or 'video').
    Raises MediaValidationError for invalid types.
    """
    if content_type not in ALLOWED_MIMES:
        raise MediaValidationError(
            f"Unsupported file type: {content_type}. "
            f"Allowed: {', '.join(sorted(ALLOWED_MIMES))}",
            detail={"content_type": content_type, "allowed": sorted(ALLOWED_MIMES)},
        )
    return "image" if content_type in ALLOWED_IMAGE_MIMES else "video"


def validate_file_size(size: int) -> None:
    """Validate file size against configured maximum."""
    if size > settings.max_upload_bytes:
        raise MediaValidationError(
            f"File too large: {size / (1024*1024):.1f} MB. "
            f"Maximum: {settings.MAX_UPLOAD_SIZE_MB} MB",
            detail={"size_bytes": size, "max_bytes": settings.max_upload_bytes},
        )


def compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def save_upload(file: BinaryIO, filename: str) -> tuple[str, str]:
    """
    Save an uploaded file to disk with a UUID-based name.
    Returns (saved_path, original_extension).
    """
    storage_dir = Path(settings.MEDIA_STORAGE_PATH)
    storage_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(filename).suffix.lower() if filename else ""
    unique_name = f"{uuid.uuid4().hex}{ext}"
    save_path = storage_dir / unique_name

    with open(save_path, "wb") as dest:
        shutil.copyfileobj(file, dest)

    return str(save_path), ext


def scan_for_viruses(file_path: str) -> None:
    """
    Scan a file with ClamAV. Raises on infection.
    Logs warning if scanner is unavailable (graceful degradation).
    """
    result = virus_scanner.scan_file(file_path)
    if result.status == ScanStatus.INFECTED:
        # Delete infected file immediately
        Path(file_path).unlink(missing_ok=True)
        from app.core.exceptions import VirusScanError
        raise VirusScanError(f"File rejected: {result.detail}")


def cleanup_file(file_path: str) -> None:
    """Remove a file from disk (used on validation failure)."""
    Path(file_path).unlink(missing_ok=True)
