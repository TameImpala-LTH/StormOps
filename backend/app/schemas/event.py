"""Pydantic schemas for Event-Based Environmental Awareness layer."""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class EnvironmentalPressureItem(BaseModel):
    """Structured environmental pressure with evidence type."""

    type: str = Field(..., description="Type of environmental pressure (traffic, noise_pollution, air_pollution, public_activity, congestion)")
    level: str = Field("elevated", description="Impact level (elevated, high, severe)")
    evidence_type: str = Field("historical_pattern", description="Evidence backing (historical_pattern, observed, authoritative)")


class EventOccurrence(BaseModel):
    """Verified yearly occurrence dates for an environmental event."""

    year: int = Field(..., description="Calendar year of occurrence (e.g. 2026)")
    start_date: str = Field(..., description="Start date in ISO format YYYY-MM-DD")
    end_date: str = Field(..., description="End date in ISO format YYYY-MM-DD")
    post_event_days: int = Field(3, description="Days after end_date where post-event activity remains elevated")


class EnvironmentalEvent(BaseModel):
    """Structured evidence-based environmental event schema."""

    id: str = Field(..., description="Unique event identifier")
    title: str = Field(..., description="Event name (e.g. Durga Puja Festival)")
    category: str = Field("festival", description="Event category (festival, sports, civic)")
    geographic_scope: List[str] = Field(..., description="Target cities or regions (e.g. ['Kolkata', 'West Bengal'])")
    occurrences: List[EventOccurrence] = Field(..., description="Verified yearly occurrences")
    environmental_pressures: List[EnvironmentalPressureItem] = Field(..., description="Structured environmental pressures")
    advisory_summary: str = Field(..., description="Evidence-backed advisory summary text")
    key_recommendations: List[str] = Field(default_factory=list, description="Practical guidance for users")
    source_metadata: str = Field(..., description="Authoritative source citation for event dates")
    status: Optional[str] = Field(None, description="Computed status: upcoming, active, post_event, expired")
    days_until: Optional[int] = Field(None, description="Computed days until start_date (0 if active/post_event)")
