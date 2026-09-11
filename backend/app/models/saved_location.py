"""SavedLocation ORM model representing a user's starred favorite places."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class SavedLocation(Base):
    """Saved location entity owned by an individual user."""

    __tablename__ = "saved_locations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    country = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="saved_locations")

    # Prevent saving the exact same coordinates repeatedly for the same user
    __table_args__ = (
        UniqueConstraint("user_id", "latitude", "longitude", name="uq_user_location_coords"),
    )

