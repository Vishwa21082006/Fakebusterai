"""
FakeBuster AI — Application Configuration
Loads all settings from environment variables via Pydantic BaseSettings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Central configuration — values loaded from .env or environment."""

    # ── App ──
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=True)

    # ── Database ──
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./fakebuster_dev.db"
    )
    DATABASE_URL_SYNC: str = Field(
        default="sqlite:///./fakebuster_dev.db"
    )

    # ── Redis ──
    REDIS_URL: str = Field(default="redis://redis:6379/0")

    # ── JWT ──
    JWT_SECRET: str = Field(default="CHANGE_ME_TO_A_RANDOM_64_CHAR_STRING")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRY_MINUTES: int = Field(default=60)

    # ── ClamAV ──
    CLAMAV_HOST: str = Field(default="clamav")
    CLAMAV_PORT: int = Field(default=3310)

    # ── Upload Limits ──
    MAX_UPLOAD_SIZE_MB: int = Field(default=50)

    # ── Rate Limiting ──
    RATE_LIMIT_REQUESTS: int = Field(default=30)
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60)

    # ── Media Storage ──
    MEDIA_STORAGE_PATH: str = Field(default="./media")

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
