"""Database schema definitions and SQLite initialization for the Nationwide India Gazetteer."""

import sqlite3
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class EntityCategory(str, Enum):
    ADMINISTRATIVE = "ADMINISTRATIVE"
    SETTLEMENT = "SETTLEMENT"
    LOCALITY = "LOCALITY"
    LANDMARK = "LANDMARK"


class EntityType(str, Enum):
    STATE_UT = "STATE_UT"
    DISTRICT = "DISTRICT"
    SUBDISTRICT = "SUBDISTRICT"
    STATUTORY_TOWN = "STATUTORY_TOWN"
    CENSUS_TOWN = "CENSUS_TOWN"
    VILLAGE = "VILLAGE"
    LOCALITY = "LOCALITY"
    NEIGHBORHOOD = "NEIGHBORHOOD"
    TRANSIT_HUB = "TRANSIT_HUB"
    JUNCTION = "JUNCTION"


class AliasType(str, Enum):
    HISTORICAL = "HISTORICAL"
    COLLOQUIAL = "COLLOQUIAL"
    PHONETIC = "PHONETIC"
    ABBREVIATION = "ABBREVIATION"
    LOCAL_SCRIPT = "LOCAL_SCRIPT"
    CURATED = "CURATED"


class RepStrategy(str, Enum):
    HQ_COORDINATE = "HQ_COORDINATE"
    CENTROID = "CENTROID"
    POPULATION_WEIGHTED = "POPULATION_WEIGHTED"
    CURATED_POINT = "CURATED_POINT"


@dataclass
class GeographicEntity:
    name: str
    normalized_name: str
    entity_category: EntityCategory
    entity_type: EntityType
    admin_level: int
    source: str
    retrieved_at: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    specific_subtype: Optional[str] = None
    parent_id: Optional[str] = None
    state_id: Optional[str] = None
    district_id: Optional[str] = None
    subdistrict_id: Optional[str] = None
    country_code: str = "IN"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    source_id: Optional[str] = None
    source_version: Optional[str] = None
    source_release_date: Optional[str] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    confidence: float = 1.0
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityAlias:
    entity_id: str
    alias: str
    normalized_alias: str
    alias_type: AliasType
    source: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    language: Optional[str] = None
    confidence: float = 1.0


@dataclass
class EntityGeometry:
    entity_id: str
    rep_latitude: float
    rep_longitude: float
    rep_strategy: RepStrategy
    source: str
    retrieved_at: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    bounding_box: Optional[str] = None  # JSON string [min_lat, min_lon, max_lat, max_lon]


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS geographic_entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    entity_category TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    specific_subtype TEXT,
    admin_level INTEGER NOT NULL,
    parent_id TEXT,
    state_id TEXT,
    district_id TEXT,
    subdistrict_id TEXT,
    country_code TEXT NOT NULL DEFAULT 'IN',
    latitude REAL,
    longitude REAL,
    source TEXT NOT NULL,
    source_id TEXT,
    source_version TEXT,
    source_release_date TEXT,
    retrieved_at TEXT NOT NULL,
    valid_from TEXT,
    valid_to TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    is_active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY(parent_id) REFERENCES geographic_entities(id)
);

CREATE INDEX IF NOT EXISTS idx_entities_norm_name ON geographic_entities(normalized_name);
CREATE INDEX IF NOT EXISTS idx_entities_parent ON geographic_entities(parent_id);
CREATE INDEX IF NOT EXISTS idx_entities_state ON geographic_entities(state_id);
CREATE INDEX IF NOT EXISTS idx_entities_district ON geographic_entities(district_id);
CREATE INDEX IF NOT EXISTS idx_entities_subdistrict ON geographic_entities(subdistrict_id);
CREATE INDEX IF NOT EXISTS idx_entities_source_id ON geographic_entities(source, source_id);

CREATE TABLE IF NOT EXISTS entity_aliases (
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    alias_type TEXT NOT NULL,
    language TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    source TEXT NOT NULL,
    FOREIGN KEY(entity_id) REFERENCES geographic_entities(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_aliases_entity ON entity_aliases(entity_id);
CREATE INDEX IF NOT EXISTS idx_aliases_norm ON entity_aliases(normalized_alias);

CREATE TABLE IF NOT EXISTS entity_geometries (
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    rep_latitude REAL NOT NULL,
    rep_longitude REAL NOT NULL,
    rep_strategy TEXT NOT NULL,
    bounding_box TEXT,
    source TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    FOREIGN KEY(entity_id) REFERENCES geographic_entities(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_geometries_entity ON entity_geometries(entity_id);

-- FTS5 Virtual Table for sub-millisecond search across canonical names and aliases
CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
    name,
    normalized_name,
    aliases,
    entity_id UNINDEXED,
    entity_category UNINDEXED,
    state_id UNINDEXED,
    district_id UNINDEXED
);
"""


def init_sqlite_schema(conn: sqlite3.Connection) -> None:
    """Initialize all gazetteer tables, indexes, and FTS5 structures."""
    conn.executescript(SCHEMA_SQL)
    conn.commit()
