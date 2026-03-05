"""
FakeBuster AI — Auth Schemas
Request/response models for authentication endpoints.
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    created_at: str

    model_config = ConfigDict(from_attributes=True)
