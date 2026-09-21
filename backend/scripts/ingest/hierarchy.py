"""Administrative hierarchy graph construction and ancestor resolution.

Historical vs Current Hierarchy
--------------------------------
Census 2011 records carry a historical parent hierarchy that reflects the
administrative structure as of 2011-03-31. The current LGD hierarchy is the
authoritative *present-day* structure. These may legitimately differ because:

  - District boundaries have been redrawn since 2011.
  - Sub-districts (tehsils/taluks) have been split or merged.
  - New districts have been carved out of older ones.

The pipeline therefore distinguishes:

  A. VALID HISTORICAL RELATIONSHIP
     A Census 2011 entity references a parent that exists in the Census 2011
     source hierarchy but does not match the current LGD parent. This is NOT
     an error. The historical relationship is preserved in the entity's
     metadata["census_parent_source_id"]. If a crosswalk to the current LGD
     parent is supplied (via metadata["lgd_crosswalk_parent_id"]), the entity's
     primary parent_id is updated to the LGD parent, but the original Census
     relationship remains in metadata.

  B. INVALID / BROKEN PARENT REFERENCE
     An entity references a parent_id (UUID) that does not exist at all in
     the entity registry. This is logged as a hard error and the entity is
     flagged but still retained so that downstream consumers can decide how to
     handle it.

Cycle detection is also performed and treated as a hard error.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple

from .schema import EntityType, GeographicEntity

logger = logging.getLogger(__name__)


class HierarchyGraph:
    """Manages parent-child administrative linkages and resolves denormalized ancestor IDs."""

    def __init__(self) -> None:
        # Primary entity registry: UUID -> entity
        self._entities: Dict[str, GeographicEntity] = {}
        # Secondary index: (source, source_id) -> UUID
        self._source_index: Dict[Tuple[str, str], str] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def add_entity(self, entity: GeographicEntity) -> None:
        """Register an entity into the hierarchy graph."""
        self._entities[entity.id] = entity
        if entity.source and entity.source_id:
            self._source_index[(entity.source, str(entity.source_id))] = entity.id

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get_entity(self, entity_id: str) -> Optional[GeographicEntity]:
        """Retrieve entity by internal UUID."""
        return self._entities.get(entity_id)

    def find_by_source_id(self, source: str, source_id: str) -> Optional[GeographicEntity]:
        """Lookup an entity by its upstream source and source-specific identifier."""
        e_id = self._source_index.get((source, str(source_id)))
        return self._entities.get(e_id) if e_id else None

    def get_all_entities(self) -> List[GeographicEntity]:
        """Return all registered entities in deterministic (source, source_id, id) order."""
        return sorted(
            self._entities.values(),
            key=lambda e: (e.source or "", e.source_id or "", e.id),
        )

    # ------------------------------------------------------------------
    # LGD Crosswalk
    # ------------------------------------------------------------------

    def apply_lgd_crosswalk(self, census_entity: GeographicEntity, lgd_parent_id: str) -> None:
        """Attach a Census entity to its current LGD parent without erasing the historical link.

        The original Census parent source_id is preserved in
        metadata["census_parent_source_id"].  The entity's primary parent_id is
        updated to point at the current LGD parent UUID so that the live
        administrative hierarchy is traversable.
        """
        # Preserve original Census parent before overwriting
        original_parent_source_id = census_entity.metadata.get("historical_census_parent")
        census_entity.metadata["census_parent_source_id"] = original_parent_source_id
        census_entity.metadata["lgd_crosswalk_applied"] = True
        census_entity.parent_id = lgd_parent_id

    # ------------------------------------------------------------------
    # Ancestor resolution
    # ------------------------------------------------------------------

    def resolve_ancestors(self) -> Tuple[List[str], List[str]]:
        """Traverse the parent graph and populate state_id, district_id, subdistrict_id shortcuts.

        Returns:
            (hard_errors, warnings)

            hard_errors: broken parent references or cycles – indicate data
                         integrity problems that must be investigated.
            warnings:    valid historical mismatches (Census parent ≠ current LGD
                         parent that have been crosswalked) – informational only.
        """
        hard_errors: List[str] = []
        warnings: List[str] = []

        for entity in self._entities.values():
            curr_id = entity.parent_id
            visited: Set[str] = {entity.id}

            while curr_id:
                # Cycle detection
                if curr_id in visited:
                    hard_errors.append(
                        f"CYCLE: entity '{entity.name}' ({entity.id}) "
                        f"has a cycle in its parent chain at node '{curr_id}'"
                    )
                    break

                visited.add(curr_id)
                parent = self._entities.get(curr_id)

                # Broken / invalid parent reference
                if parent is None:
                    hard_errors.append(
                        f"INVALID_PARENT: entity '{entity.name}' (id={entity.id}, "
                        f"source={entity.source}, source_id={entity.source_id}) "
                        f"references non-existent parent_id='{curr_id}'"
                    )
                    break

                # Historical crosswalk informational note
                if entity.metadata.get("lgd_crosswalk_applied") and entity.metadata.get("census_parent_source_id"):
                    warnings.append(
                        f"HISTORICAL_CROSSWALK: '{entity.name}' (source={entity.source}) "
                        f"original Census parent source_id='{entity.metadata['census_parent_source_id']}' "
                        f"remapped to LGD parent_id='{entity.parent_id}'"
                    )

                # Populate ancestor shortcuts (first match wins per level)
                if (parent.entity_type == EntityType.STATE_UT or parent.admin_level == 1):
                    if not entity.state_id:
                        entity.state_id = parent.id
                elif (parent.entity_type == EntityType.DISTRICT or parent.admin_level == 2):
                    if not entity.district_id:
                        entity.district_id = parent.id
                elif (parent.entity_type == EntityType.SUBDISTRICT or parent.admin_level == 3):
                    if not entity.subdistrict_id:
                        entity.subdistrict_id = parent.id

                curr_id = parent.parent_id

        return hard_errors, warnings
