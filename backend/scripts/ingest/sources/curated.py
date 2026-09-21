"""Source adapter for the existing curated urban locality index.

Isolation Contract
-------------------
This adapter reads backend/app/data/india_localities.json as a plain JSON file.
It MUST NOT import any runtime application module (no backend.app.services.*,
no backend.app.models.*, etc.). The file path is resolved relative to this
adapter's location in the repository to avoid any hard-coded absolute paths.

Source Label
------------
All entities produced by this adapter carry source="CURATED_URBAN".  This
distinguishes them from LGD, Census, and OSM records in the deduplication and
hierarchy stages.

Entity Mapping
--------------
Each curated locality entry has the following optional fields in the JSON:

    name        – locality name (required)
    city        – parent city name (optional)
    district    – district name (optional)
    state       – state name (optional)
    latitude    – representative point (optional)
    longitude   – representative point (optional)
    aliases     – list of source-provided alternate name strings (optional)
    landmark    – boolean, if True entity_type is set to TRANSIT_HUB or LANDMARK

Alias Policy
------------
Only aliases explicitly listed in the source JSON are emitted as EntityAlias
records. No aliases are fabricated from the entry's city, district, or state
fields; those are stored in entity metadata for context only.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple

from ..normalize import normalize_name
from ..schema import (
    AliasType,
    EntityAlias,
    EntityCategory,
    EntityGeometry,
    EntityType,
    GeographicEntity,
    RepStrategy,
)
from .base import SourceAdapter

# Resolve the curated JSON path relative to this file so no absolute path is
# hard-coded (the ingestion package lives at backend/scripts/ingest/sources/).
_CURATED_JSON_PATH = (
    Path(__file__).resolve().parents[3]  # → backend/
    / "app"
    / "data"
    / "india_localities.json"
)


class CuratedAdapter(SourceAdapter):
    """Imports the existing curated urban locality index as source CURATED_URBAN.

    The adapter accepts an optional explicit path (for testing with fixture files).
    When no path is supplied it falls back to the canonical repository location.
    """

    def __init__(self, json_path: Optional[str] = None) -> None:
        self._json_path = Path(json_path) if json_path else _CURATED_JSON_PATH

    @property
    def source_name(self) -> str:
        return "CURATED_URBAN"

    def parse(
        self, data_or_path: Any = None
    ) -> Tuple[List[GeographicEntity], List[EntityAlias], List[EntityGeometry]]:
        """Load and parse the curated locality JSON.

        data_or_path may be:
          - None            → load from self._json_path (default)
          - str / Path      → treat as file path and load from it
          - list            → treat as pre-parsed list of locality dicts (for tests)
        """
        entities: List[GeographicEntity] = []
        aliases: List[EntityAlias] = []
        geometries: List[EntityGeometry] = []
        retrieved_at = datetime.now(timezone.utc).isoformat()

        if isinstance(data_or_path, list):
            items = data_or_path
        elif data_or_path is not None:
            with open(str(data_or_path), encoding="utf-8") as fh:
                items = json.load(fh)
        else:
            with open(str(self._json_path), encoding="utf-8") as fh:
                items = json.load(fh)

        for idx, item in enumerate(items):
            name = item.get("name", "").strip()
            if not name:
                continue

            norm = normalize_name(name)

            # Determine entity type
            is_landmark = bool(item.get("landmark", False))
            if is_landmark:
                cat = EntityCategory.LANDMARK
                etype = EntityType.TRANSIT_HUB  # default landmark subtype
                admin_lvl = 6
                subtype = "Landmark"
            else:
                cat = EntityCategory.LOCALITY
                etype = EntityType.LOCALITY
                admin_lvl = 5
                subtype = "Urban Locality"

            lat: Optional[float] = (
                float(item["latitude"])
                if "latitude" in item and item["latitude"] is not None
                else None
            )
            lon: Optional[float] = (
                float(item["longitude"])
                if "longitude" in item and item["longitude"] is not None
                else None
            )

            # Use a deterministic source_id based on position and name when no
            # official code is available (curated data does not carry source codes)
            source_id = item.get("source_id") or f"CURATED_{idx:05d}_{normalize_name(name)}"

            e = GeographicEntity(
                name=name,
                normalized_name=norm,
                entity_category=cat,
                entity_type=etype,
                admin_level=admin_lvl,
                specific_subtype=subtype,
                source=self.source_name,
                source_id=source_id,
                source_version="CURATED_V1",
                source_release_date=None,
                valid_from=None,
                valid_to=None,
                confidence=float(item.get("confidence", 0.90)),
                retrieved_at=retrieved_at,
                parent_id=item.get("parent_id"),
                state_id=item.get("state_id"),
                district_id=item.get("district_id"),
                subdistrict_id=item.get("subdistrict_id"),
                latitude=lat,
                longitude=lon,
                metadata={
                    # Contextual labels for reference only — not converted to aliases
                    "city_label": item.get("city"),
                    "district_label": item.get("district"),
                    "state_label": item.get("state"),
                },
            )
            entities.append(e)

            # Source-provided aliases only (explicit list in the JSON)
            for alt in item.get("aliases", []):
                alt = alt.strip()
                if not alt or alt == name:
                    continue
                norm_alt = normalize_name(alt)
                aliases.append(
                    EntityAlias(
                        entity_id=e.id,
                        alias=alt,
                        normalized_alias=norm_alt,
                        alias_type=AliasType.CURATED,
                        language="en",
                        confidence=0.90,
                        source=self.source_name,
                    )
                )

            # Geometry
            if lat is not None and lon is not None:
                g = EntityGeometry(
                    entity_id=e.id,
                    rep_latitude=lat,
                    rep_longitude=lon,
                    rep_strategy=RepStrategy.CURATED_POINT,
                    source=self.source_name,
                    retrieved_at=retrieved_at,
                )
                geometries.append(g)

        return entities, aliases, geometries
