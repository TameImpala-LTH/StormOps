"""Internal data transfer models for parsed and normalized advisories."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class NormalizedAdvisory:
    """In-memory normalized advisory produced by source provider adapters."""

    source_id: str
    authority: str
    hazard_type: str
    severity: str
    issued_at: datetime
    effective_at: datetime
    expires_at: datetime
    headline: str
    description: str
    source_url: Optional[str] = None
    official_level: Optional[str] = None
    urgency: Optional[str] = None
    certainty: Optional[str] = None
    granularity: str = "district"
    state: Optional[str] = None
    district: Optional[str] = None
    subdivision: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = None
    polygon_geojson: Optional[str] = None
    action_guidance: Optional[str] = None
    raw_payload: Dict[str, Any] = field(default_factory=dict)
