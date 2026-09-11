"""Pydantic schemas for authenticated user Environmental Outlook."""

from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.event import EnvironmentalPressureItem


class EnvironmentalOutlookItem(BaseModel):
    """Structured evidence-based environmental period item for the user's outlook."""

    event_id: str = Field(..., description="Unique event identifier")
    event_title: str = Field(..., description="Event name (e.g. Durga Puja Festival)")
    category: str = Field("festival", description="Event category")
    location_name: str = Field(..., description="Name of the saved or viewed location that triggered this event")
    start_date: str = Field(..., description="Start date in ISO format YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="End date in ISO format YYYY-MM-DD")
    post_event_days: int = Field(3, description="Days after end date where post-event activity remains elevated")
    status: str = Field(..., description="Current status: active, upcoming, post_event")
    days_until: Optional[int] = Field(None, description="Days until start (0 if active/post_event)")
    advisory_summary: str = Field(..., description="Concise evidence-backed description")
    evidence_note: str = Field(
        "Historically associated with increased local environmental pressure.",
        description="Standard non-predictive evidence statement",
    )
    environmental_pressures: List[EnvironmentalPressureItem] = Field(
        default_factory=list,
        description="Structured environmental pressures (traffic, noise, congestion, crowd density)",
    )
    key_recommendations: List[str] = Field(
        default_factory=list,
        description="Practical recommendations",
    )
    source_metadata: str = Field(..., description="Authoritative source citation for event dates")


class EnvironmentalOutlookResponse(BaseModel):
    """Response containing the authenticated user's environmental outlook items."""

    items: List[EnvironmentalOutlookItem] = Field(
        default_factory=list,
        description="Chronologically and priority sorted environmental outlook items",
    )
    total_events: int = Field(0, description="Total count of active/upcoming environmental events")
    locations_evaluated: List[str] = Field(
        default_factory=list,
        description="List of location names evaluated for this outlook",
    )
