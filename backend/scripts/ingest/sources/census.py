"""Source adapter for Census of India 2011 settlement records.

Census 2011 is the authoritative HISTORICAL SETTLEMENT BASELINE. It represents
geographic and administrative data as of the Census reference date (2011-03-31).
The parent hierarchy recorded here reflects the administrative structure at that
point in time and may differ from the current LGD hierarchy.

Handling Historical Hierarchy
------------------------------
Each entity produced by this adapter stores:

  metadata["historical_census_parent"]
      The census_code (Census 2011 source_id) of the parent record as supplied
      in the Census data. This preserves the original historical relationship.

  metadata["lgd_crosswalk_parent_id"]  (optional)
      If the source record supplies a crosswalk to the current LGD parent code,
      this field is populated. The HierarchyGraph.apply_lgd_crosswalk() method
      uses this value to attach the entity to the live administrative hierarchy
      without erasing the historical link.

Historical parent relationships that differ from the current LGD hierarchy are
NOT treated as errors by this adapter. Validation of such differences is the
responsibility of the hierarchy resolution stage.
"""

from datetime import datetime, timezone
from typing import Any, List, Tuple

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


class CensusAdapter(SourceAdapter):
    """Parses historical settlement and geographic baseline records from Census of India 2011."""

    @property
    def source_name(self) -> str:
        return "CENSUS_2011"

    def parse(
        self, data_or_path: Any
    ) -> Tuple[List[GeographicEntity], List[EntityAlias], List[EntityGeometry]]:
        """Parse a list of Census 2011 settlement records.

        Each record dict may contain:
            name                    – settlement name (required)
            census_2011_code        – Census source identifier (or 'census_code')
            settlement_type         – STATUTORY_TOWN | CENSUS_TOWN | VILLAGE
            latitude / longitude    – representative point (optional)
            parent_id               – internal UUID of parent entity (optional)
            state_id / district_id / subdistrict_id – optional hierarchy UUIDs
            lgd_crosswalk_parent_id – optional current LGD parent LGD code,
                                      stored in metadata for crosswalk resolution
            alt_names               – list of source-provided alternate name strings
            confidence              – float 0.0–1.0 (default 0.95)
        """
        entities: List[GeographicEntity] = []
        aliases: List[EntityAlias] = []
        geometries: List[EntityGeometry] = []
        retrieved_at = datetime.now(timezone.utc).isoformat()

        items = data_or_path if isinstance(data_or_path, list) else data_or_path.get("records", [])

        for item in items:
            name = item.get("name", "").strip()
            if not name:
                continue

            norm = normalize_name(name)
            census_code = str(
                item.get("census_2011_code") or item.get("census_code") or ""
            )
            settlement_type = item.get("settlement_type", "").upper()

            # Map settlement type to entity category / type
            if settlement_type == "STATUTORY_TOWN":
                cat = EntityCategory.SETTLEMENT
                etype = EntityType.STATUTORY_TOWN
                admin_lvl = 4
                subtype = item.get("subtype", "Statutory Town")
            elif settlement_type == "CENSUS_TOWN":
                cat = EntityCategory.SETTLEMENT
                etype = EntityType.CENSUS_TOWN
                admin_lvl = 4
                subtype = "Census Town"
            else:
                # Default: Revenue Village
                cat = EntityCategory.SETTLEMENT
                etype = EntityType.VILLAGE
                admin_lvl = 4
                subtype = "Revenue Village"

            lat = (
                float(item["latitude"])
                if "latitude" in item and item["latitude"] is not None
                else None
            )
            lon = (
                float(item["longitude"])
                if "longitude" in item and item["longitude"] is not None
                else None
            )

            # Preserve historical Census parent reference and optional LGD crosswalk
            historical_census_parent = item.get("historical_census_parent") or item.get("parent_census_code")
            lgd_crosswalk_parent_id = item.get("lgd_crosswalk_parent_id")

            e = GeographicEntity(
                name=name,
                normalized_name=norm,
                entity_category=cat,
                entity_type=etype,
                admin_level=admin_lvl,
                specific_subtype=subtype,
                source=self.source_name,
                source_id=census_code,
                source_version="CENSUS_2011_V1",
                source_release_date="2011-03-31",
                valid_from="2011-03-31",
                valid_to=None,  # Status not superseded; historical record persists
                confidence=float(item.get("confidence", 0.95)),
                retrieved_at=retrieved_at,
                parent_id=item.get("parent_id"),
                state_id=item.get("state_id"),
                district_id=item.get("district_id"),
                subdistrict_id=item.get("subdistrict_id"),
                latitude=lat,
                longitude=lon,
                metadata={
                    # Preserve the original Census parent source_id verbatim
                    "historical_census_parent": historical_census_parent,
                    # Optional crosswalk to the current LGD parent (source code, not UUID)
                    "lgd_crosswalk_parent_id": lgd_crosswalk_parent_id,
                },
            )
            entities.append(e)

            # Source-provided alternate names (genuine aliases only)
            for alt in item.get("alt_names", []):
                alt = alt.strip()
                if not alt or alt == name:
                    continue
                norm_alt = normalize_name(alt)
                aliases.append(
                    EntityAlias(
                        entity_id=e.id,
                        alias=alt,
                        normalized_alias=norm_alt,
                        alias_type=AliasType.COLLOQUIAL,
                        language=item.get("alt_name_language", "en"),
                        confidence=0.90,
                        source=self.source_name,
                    )
                )

            # Geometry (representative centroid point)
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
