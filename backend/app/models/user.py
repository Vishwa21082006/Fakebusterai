"""
FakeBuster AI — User ORM Model
Supports JWT auth with role-based access control.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Uuid
)
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        Uuid, primary_key=True, default=uuid.uuid4, index=True
    )
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(Text, nullable=False)
    role = Column(
        String(16),
        nullable=False,
        default="user",
    )
    is_active = Column(Boolean, default=True, nullable=False)
    api_key = Column(String(64), unique=True, nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    analyses = relationship("Analysis", back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User {self.email} role={self.role}>"
