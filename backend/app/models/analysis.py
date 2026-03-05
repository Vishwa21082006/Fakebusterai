"""
FakeBuster AI — Analysis ORM Model
Tracks every media analysis job: status, results, model version.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Float, DateTime, Text, ForeignKey, JSON, Uuid
)
from sqlalchemy.orm import relationship

from app.database import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(
        Uuid, primary_key=True, default=uuid.uuid4, index=True
    )
    user_id = Column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    source_type = Column(
        String(16), nullable=False
    )
    source_ref = Column(Text, nullable=False)  # file path or URL
    media_type = Column(
        String(16), nullable=False
    )
    status = Column(
        String(16),
        nullable=False,
        default="queued",
    )
    result_score = Column(Float, nullable=True)  # 0.0 = real, 1.0 = fake
    result_detail = Column(JSON, nullable=True)  # full layer breakdown
    model_version = Column(String(32), nullable=True)
    file_hash = Column(String(128), nullable=True)  # SHA-256
    error_message = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="analyses")

    def __repr__(self) -> str:
        return f"<Analysis {self.id} status={self.status} score={self.result_score}>"
