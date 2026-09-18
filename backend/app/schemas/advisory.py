"""Pydantic schemas for official environmental and hazard advisories."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AdvisoryBase(BaseModel):
    """Base advisory schema with core meteorological and disaster attributes."""

    source_id: str = Field(..., description="Original identifier assigned by the issuing authority")
    authority: str = Field(..., description="Issuing authority (IMD, NDMA, CWC, INCOIS, CPCB, etc.)")
    source_url: Optional[str] = Field(None, description="Direct URL to official bulletin or alert entry")
    hazard_type: str = Field(..., description="Normalized hazard category (HEAVY_RAIN, HEATWAVE, CYCLONE, etc.)")
    severity: str = Field(..., description="Normalized severity level: green, yellow, orange, red, unknown")
    official_level: Optional[str] = Field(None, description="Verbatim official severity designation from source")
    urgency: Optional[str] = Field(None, description="Alert urgency: immediate, expected, future, past")
    certainty: Optional[str] = Field(None, description="Alert certainty: observed, likely, possible, unlikely")
    issued_at: datetime = Field(..., description="UTC timestamp when alert was officially issued")
    effective_at: datetime = Field(..., description="UTC timestamp when alert becomes active")
    expires_at: datetime = Field(..., description="UTC timestamp when alert ceases to be valid")
    is_active: bool = Field(True, description="Whether alert is currently in effect")
    granularity: str = Field("district", description="Geographic scope tier: nowcast, district, subdivision, state")
    state: Optional[str] = Field(None, description="Target state or union territory name")
    district: Optional[str] = Field(None, description="Target administrative district name")
    subdivision: Optional[str] = Field(None, description="IMD meteorological subdivision name")
    latitude: Optional[float] = Field(None, description="Center latitude coordinate for point/circle alerts")
    longitude: Optional[float] = Field(None, description="Center longitude coordinate for point/circle alerts")
    radius_km: Optional[float] = Field(None, description="Affected radius in kilometers")
    polygon_geojson: Optional[str] = Field(None, description="GeoJSON polygon or multipolygon representation")
    headline: str = Field(..., description="Concise official hazard warning headline")
    description: str = Field(..., description="Full official meteorological / hazard description")
    action_guidance: Optional[str] = Field(None, description="Public safety instructions issued by authorities")
    raw_payload: Optional[Dict[str, Any]] = Field(None, description="Original source payload for provenance")


class AdvisoryCreate(AdvisoryBase):
    """Schema for upserting or creating an ingested hazard advisory."""

    pass


class AdvisoryResponse(AdvisoryBase):
    """API response schema for an individual official hazard advisory."""

    id: str = Field(..., description="System-generated unique identifier")
    created_at: datetime = Field(..., description="Ingestion timestamp")
    updated_at: datetime = Field(..., description="Last revision timestamp")

    model_config = ConfigDict(from_attributes=True)


class AdvisoryQueryFilter(BaseModel):
    """Query filter parameters for retrieving location-matched advisories."""

    district: Optional[str] = None
    state: Optional[str] = None
    subdivision: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    authority: Optional[str] = None
    hazard_type: Optional[str] = None
    severity: Optional[str] = None
    include_expired: bool = False


class AdvisoryListResponse(BaseModel):
    """Response payload containing list of active advisories with metadata."""

    total: int
    advisories: List[AdvisoryResponse]
    district: Optional[str] = None
    state: Optional[str] = None
    timestamp: datetime
