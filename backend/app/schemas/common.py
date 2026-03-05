"""
FakeBuster AI — Common Schemas
Shared response models used across the API.
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    db: bool
    redis: bool
    clamav: bool


class ErrorResponse(BaseModel):
    error: bool = True
    message: str
    detail: dict = {}


class MessageResponse(BaseModel):
    message: str
