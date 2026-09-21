"""Source adapter for Government of India Local Government Directory (LGD) records."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from ..normalize import normalize_name
from ..schema import (
    EntityCategory,
    EntityType,
    EntityAlias,
    EntityGeometry,
    GeographicEntity,
)
from .base import SourceAdapter


class LGDAdapter(SourceAdapter):
    """Parses authoritative administrative records from the Local Government Directory."""

    @property
    def source_name(self) -> str:
        return "LGD"

    def parse(
        self, data_or_path: Any
    ) -> Tuple[List[GeographicEntity], List[EntityAlias], List[EntityGeometry]]:
        """Parse structured LGD dataset dictionaries or list of records."""
        entities: List[GeographicEntity] = []
        aliases: List[EntityAlias] = []
        geometries: List[EntityGeometry] = []
        retrieved_at = datetime.now(timezone.utc).isoformat()

        items = data_or_path if isinstance(data_or_path, list) else data_or_path.get("records", [])

        for item in items:
            level = item.get("level", "").lower()
            name = item.get("name", "").strip()
            norm = normalize_name(name)
            source_id = str(item.get("lgd_code") or item.get("source_id") or "")
            source_ver = item.get("source_version", "LGD_CURRENT")
            source_date = item.get("source_release_date")
            valid_from = item.get("valid_from")
            valid_to = item.get("valid_to")

            if level in ("state", "state_ut"):
                cat = EntityCategory.ADMINISTRATIVE
                etype = EntityType.STATE_UT
                admin_lvl = 1
                subtype = "State" if "state" in item.get("type", "state").lower() else "Union Territory"
            elif level == "district":
                cat = EntityCategory.ADMINISTRATIVE
                etype = EntityType.DISTRICT
                admin_lvl = 2
                subtype = item.get("subtype", "District")
            elif level in ("subdistrict", "sub_district", "tehsil", "taluk", "mandal", "block"):
                cat = EntityCategory.ADMINISTRATIVE
                etype = EntityType.SUBDISTRICT
                admin_lvl = 3
                # Preserve regional administrative terminology
                subtype = item.get("subtype") or item.get("subdistrict_type") or "Sub-District"
            elif level in ("ulb", "town", "city", "corporation"):
                cat = EntityCategory.SETTLEMENT
                etype = EntityType.STATUTORY_TOWN
                admin_lvl = 4
                subtype = item.get("subtype") or "Urban Local Body"
            elif level == "village":
                cat = EntityCategory.SETTLEMENT
                etype = EntityType.VILLAGE
                admin_lvl = 4
                subtype = "Revenue Village"
            else:
                cat = EntityCategory.ADMINISTRATIVE
                etype = EntityType.SUBDISTRICT
                admin_lvl = 3
                subtype = item.get("subtype", "Administrative Unit")

            e = GeographicEntity(
                name=name,
                normalized_name=norm,
                entity_category=cat,
                entity_type=etype,
                admin_level=admin_lvl,
                specific_subtype=subtype,
                source=self.source_name,
                source_id=source_id,
                source_version=source_ver,
                source_release_date=source_date,
                valid_from=valid_from,
                valid_to=valid_to,
                confidence=float(item.get("confidence", 1.0)),
                retrieved_at=retrieved_at,
                parent_id=item.get("parent_id"),
                state_id=item.get("state_id"),
                district_id=item.get("district_id"),
                subdistrict_id=item.get("subdistrict_id"),
                latitude=float(item["latitude"]) if "latitude" in item and item["latitude"] is not None else None,
                longitude=float(item["longitude"]) if "longitude" in item and item["longitude"] is not None else None,
                metadata={"lgd_parent_code": item.get("parent_lgd_code")},
            )
            entities.append(e)

        return entities, aliases, geometries
