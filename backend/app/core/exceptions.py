"""
FakeBuster AI — Custom Exception Handlers
Standardized error responses across the API.
"""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class FakeBusterError(Exception):
    """Base exception for FakeBuster application errors."""
    def __init__(self, message: str, status_code: int = 500, detail: dict = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(self.message)


class MediaValidationError(FakeBusterError):
    """Raised when uploaded/ingested media fails validation."""
    def __init__(self, message: str, detail: dict = None):
        super().__init__(message, status_code=422, detail=detail)


class VirusScanError(FakeBusterError):
    """Raised when a file is detected as infected."""
    def __init__(self, message: str = "File rejected: potential malware detected"):
        super().__init__(message, status_code=400)


class URLIngestionError(FakeBusterError):
    """Raised when URL ingestion fails (404, 403, timeout, etc.)."""
    def __init__(self, message: str, detail: dict = None):
        super().__init__(message, status_code=422, detail=detail)


async def fakebuster_error_handler(request: Request, exc: FakeBusterError):
    """Global handler for FakeBuster application errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.message,
            "detail": exc.detail,
        },
    )
