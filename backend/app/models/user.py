"""User ORM model representing registered individual consumers."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    """User account model for consumer multi-user architecture."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships (isolated per user)
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    saved_locations = relationship("SavedLocation", back_populates="user", cascade="all, delete-orphan")

