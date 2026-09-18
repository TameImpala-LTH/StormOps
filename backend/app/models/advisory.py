"""Advisory ORM model representing official environmental, meteorological, and disaster warnings."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
)

from app.db.base import Base


class Advisory(Base):
    """Normalized official hazard advisory entity ingested from authoritative government sources."""

    __tablename__ = "advisories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String(255), nullable=False, index=True)
    authority = Column(String(50), nullable=False, index=True)  # e.g. IMD, NDMA, CWC, INCOIS, CPCB
    source_url = Column(String(500), nullable=True)

    # Classification & Severity
    hazard_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)  # green, yellow, orange, red, unknown
    official_level = Column(String(100), nullable=True)  # Preserves raw source term: Watch, Warning, Danger Level
    urgency = Column(String(20), nullable=True)  # immediate, expected, future, past
    certainty = Column(String(20), nullable=True)  # observed, likely, possible, unlikely

    # Temporal Validity (UTC)
    issued_at = Column(DateTime(timezone=True), nullable=False)
    effective_at = Column(DateTime(timezone=True), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # Geographic Scope
    granularity = Column(String(20), nullable=False, default="district")  # nowcast, district, subdivision, state
    state = Column(String(100), nullable=True, index=True)
    district = Column(String(100), nullable=True, index=True)
    subdivision = Column(String(100), nullable=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    radius_km = Column(Float, nullable=True)
    polygon_geojson = Column(Text, nullable=True)

    # Content
    headline = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    action_guidance = Column(Text, nullable=True)

    # Provenance & Audit
    raw_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("authority", "source_id", name="uq_advisory_authority_source_id"),
        Index("ix_advisories_active_expiry", "is_active", "expires_at"),
        Index("ix_advisories_geo_lookup", "state", "district", "is_active"),
        Index("ix_advisories_severity_active", "severity", "is_active"),
    )
