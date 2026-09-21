"""Source adapter for OpenStreetMap locality / place enrichment.

OSM Alias Policy
-----------------
This adapter generates aliases ONLY from names that are explicitly supplied
by the OSM source data:

  name        – canonical OSM name (always present)
  name:en     – English transliteration (genuine alternate name if different)
  alt_name    – pipe-separated OSM alternate names
  old_name    – historical/former name

It does NOT generate artificial aliases such as:
  - "Name (OSM)"
  - "Name, City"
  - Any concatenation or qualified-query form

Qualified query forms such as "Park Street, Kolkata" are geographic query context
(handled by the runtime query parser) and must NOT be stored as entity aliases.

Place Type Mapping
-------------------
OSM place tag        → EntityCategory / EntityType
----------------------------------------------------
city / town          → SETTLEMENT / STATUTORY_TOWN
village / hamlet     → SETTLEMENT / VILLAGE
suburb / quarter     → LOCALITY / LOCALITY
neighbourhood        → LOCALITY / NEIGHBORHOOD
locality             → LOCALITY / LOCALITY
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

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

# Mapping from OSM place tag to (EntityCategory, EntityType, admin_level)
_PLACE_TYPE_MAP: Dict[str, Tuple[EntityCategory, EntityType, int]] = {
    "city":          (EntityCategory.SETTLEMENT, EntityType.STATUTORY_TOWN, 4),
    "town":          (EntityCategory.SETTLEMENT, EntityType.STATUTORY_TOWN, 4),
    "village":       (EntityCategory.SETTLEMENT, EntityType.VILLAGE, 4),
    "hamlet":        (EntityCategory.SETTLEMENT, EntityType.VILLAGE, 5),
    "suburb":        (EntityCategory.LOCALITY,   EntityType.LOCALITY,        5),
    "quarter":       (EntityCategory.LOCALITY,   EntityType.LOCALITY,        5),
    "neighbourhood": (EntityCategory.LOCALITY,   EntityType.NEIGHBORHOOD,    5),
    "locality":      (EntityCategory.LOCALITY,   EntityType.LOCALITY,        5),
}

_DEFAULT_TYPE = (EntityCategory.LOCALITY, EntityType.LOCALITY, 5)


class OSMAdapter(SourceAdapter):
    """Parses OpenStreetMap place features for locality / neighbourhood enrichment."""

    @property
    def source_name(self) -> str:
        return "OSM"

    def parse(
        self, data_or_path: Any
    ) -> Tuple[List[GeographicEntity], List[EntityAlias], List[EntityGeometry]]:
        """Parse an OSM-style JSON feature list.

        Each item should be a dict with keys:
            osm_id          – OSM node/way/relation ID (string, required)
            place           – OSM place tag value (e.g. "suburb", "village")
            name            – primary name (required)
            name:en         – English name (optional; alias if different from name)
            alt_name        – pipe-separated genuine alternate names (optional)
            old_name        – historical/former name (optional; alias)
            latitude        – representative point latitude (optional)
            longitude       – representative point longitude (optional)
            state           – state name string (optional, for context only)
            district        – district name string (optional, for context only)
            state_id        – internal state entity UUID (optional)
            district_id     – internal district entity UUID (optional)
            subdistrict_id  – internal subdistrict entity UUID (optional)
            parent_id       – internal parent entity UUID (optional)
            confidence      – float 0.0–1.0 (default 0.85)
        """
        entities: List[GeographicEntity] = []
        aliases: List[EntityAlias] = []
        geometries: List[EntityGeometry] = []
        retrieved_at = datetime.now(timezone.utc).isoformat()

        items = data_or_path if isinstance(data_or_path, list) else data_or_path.get("features", [])

        for item in items:
            name = item.get("name", "").strip()
            if not name:
                continue

            norm = normalize_name(name)
            osm_id = str(item.get("osm_id") or "")
            place_tag = item.get("place", "locality").lower()
            cat, etype, admin_lvl = _PLACE_TYPE_MAP.get(place_tag, _DEFAULT_TYPE)

            lat: Optional[float] = (
                float(item["latitude"]) if "latitude" in item and item["latitude"] is not None else None
            )
            lon: Optional[float] = (
                float(item["longitude"]) if "longitude" in item and item["longitude"] is not None else None
            )

            e = GeographicEntity(
                name=name,
                normalized_name=norm,
                entity_category=cat,
                entity_type=etype,
                admin_level=admin_lvl,
                specific_subtype=item.get("place", "locality").capitalize(),
                source=self.source_name,
                source_id=osm_id,
                source_version=item.get("osm_version", "OSM_SNAPSHOT"),
                source_release_date=item.get("osm_date"),
                valid_from=item.get("osm_date"),
                valid_to=None,
                confidence=float(item.get("confidence", 0.85)),
                retrieved_at=retrieved_at,
                parent_id=item.get("parent_id"),
                state_id=item.get("state_id"),
                district_id=item.get("district_id"),
                subdistrict_id=item.get("subdistrict_id"),
                latitude=lat,
                longitude=lon,
                metadata={
                    "osm_place_tag": place_tag,
                    "state_label": item.get("state"),
                    "district_label": item.get("district"),
                },
            )
            entities.append(e)

            # --- Genuine aliases only ---

            seen_norms = {norm}

            def _add_alias(
                alias_str: str,
                alias_type: AliasType,
                language: str = "en",
                confidence: float = 0.95,
            ) -> None:
                """Add alias only if it differs from the canonical name."""
                alias_str = alias_str.strip()
                if not alias_str:
                    return
                norm_a = normalize_name(alias_str)
                if norm_a in seen_norms:
                    return  # Identical to canonical or already added
                seen_norms.add(norm_a)
                aliases.append(
                    EntityAlias(
                        entity_id=e.id,
                        alias=alias_str,
                        normalized_alias=norm_a,
                        alias_type=alias_type,
                        language=language,
                        confidence=confidence,
                        source=self.source_name,
                    )
                )

            # name:en — genuine English transliteration/alternate name
            name_en = item.get("name:en", "").strip()
            if name_en and name_en != name:
                _add_alias(name_en, AliasType.COLLOQUIAL, language="en", confidence=0.95)

            # alt_name — pipe-separated official OSM alternate names
            for alt in item.get("alt_name", "").split("|"):
                alt = alt.strip()
                if alt:
                    _add_alias(alt, AliasType.COLLOQUIAL, language="en", confidence=0.90)

            # old_name — historical former name from OSM
            old_name = item.get("old_name", "").strip()
            if old_name:
                _add_alias(old_name, AliasType.HISTORICAL, language="en", confidence=0.90)

            # Geometry
            if lat is not None and lon is not None:
                g = EntityGeometry(
                    entity_id=e.id,
                    rep_latitude=lat,
                    rep_longitude=lon,
                    rep_strategy=RepStrategy.CENTROID,
                    source=self.source_name,
                    retrieved_at=retrieved_at,
                )
                geometries.append(g)

        return entities, aliases, geometries
