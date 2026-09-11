"""Pydantic schemas for user-owned saved locations."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SavedLocationCreate(BaseModel):
    """Schema for saving a favorite location."""

    name: str = Field(..., min_length=1, max_length=255, description="Location display name")
    latitude: float = Field(..., description="Geographical latitude coordinate")
    longitude: float = Field(..., description="Geographical longitude coordinate")
    country: Optional[str] = Field(None, max_length=100, description="Country name")


class SavedLocationResponse(BaseModel):
    """Public representation of a user's saved location."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    latitude: float
    longitude: float
    country: Optional[str] = None
    created_at: datetime
