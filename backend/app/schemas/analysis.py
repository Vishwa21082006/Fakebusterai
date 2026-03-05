"""
FakeBuster AI — Analysis Schemas
Request/response models for analysis endpoints.
"""

from typing import Optional
from pydantic import BaseModel, HttpUrl, Field, ConfigDict


class URLIngestRequest(BaseModel):
    url: HttpUrl = Field(..., description="Public URL to image or video")


class AnalysisResponse(BaseModel):
    id: str
    source_type: str
    media_type: str
    status: str
    result_score: Optional[float] = None
    result_detail: Optional[dict] = None
    model_version: Optional[str] = None
    file_hash: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AnalysisListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AnalysisResponse]


class DetectRequest(BaseModel):
    """Enterprise API — inline detection request."""
    url: Optional[HttpUrl] = None
    # File can also be provided via multipart


class DetectResponse(BaseModel):
    analysis_id: str
    status: str
    result_score: Optional[float] = None
    result_detail: Optional[dict] = None
    model_version: Optional[str] = None
