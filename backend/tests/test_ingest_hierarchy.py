"""Tests for the HierarchyGraph: ancestor resolution, crosswalk, and error classification."""

import pytest

from backend.scripts.ingest.hierarchy import HierarchyGraph
from backend.scripts.ingest.schema import EntityCategory, EntityType, GeographicEntity


def _entity(name, source, source_id, etype, admin_lvl, parent_id=None,
             state_id=None, district_id=None, subdistrict_id=None):
    e = GeographicEntity(
        name=name,
        normalized_name=name.lower().replace(" ", ""),
        entity_category=EntityCategory.ADMINISTRATIVE,
        entity_type=etype,
        admin_level=admin_lvl,
        source=source,
        source_id=source_id,
        retrieved_at="2024-01-01T00:00:00+00:00",
    )
    e.parent_id = parent_id
    e.state_id = state_id
    e.district_id = district_id
    e.subdistrict_id = subdistrict_id
    return e


class TestHierarchyGraph:

    def _build_basic_graph(self):
        """State → District → Village chain."""
        state = _entity("West Bengal", "LGD", "LGD_WB", EntityType.STATE_UT, 1)
        district = _entity("Kolkata", "LGD", "LGD_WB_KOL", EntityType.DISTRICT, 2,
                            parent_id=state.id, state_id=state.id)
        village = _entity("Tangra", "LGD", "LGD_WB_KOL_TANGRA", EntityType.VILLAGE, 4,
                           parent_id=district.id, state_id=state.id, district_id=district.id)
        g = HierarchyGraph()
        for e in [state, district, village]:
            g.add_entity(e)
        return g, state, district, village

    def test_resolve_ancestors_no_errors(self):
        g, *_ = self._build_basic_graph()
        hard_errors, warnings = g.resolve_ancestors()
        assert hard_errors == [], f"No hard errors expected; got: {hard_errors}"

    def test_find_by_source_id(self):
        g, state, *_ = self._build_basic_graph()
        found = g.find_by_source_id("LGD", "LGD_WB")
        assert found is not None
        assert found.id == state.id

    def test_invalid_parent_is_hard_error(self):
        """Scenario D: entity references a parent_id that does not exist → hard error."""
        g = HierarchyGraph()
        orphan = _entity("Ghostpur", "LGD", "LGD_GHOST", EntityType.VILLAGE, 4,
                          parent_id="NONEXISTENT_UUID_12345")
        g.add_entity(orphan)
        hard_errors, warnings = g.resolve_ancestors()
        assert any("INVALID_PARENT" in e for e in hard_errors), (
            "Missing parent UUID must produce an INVALID_PARENT hard error"
        )

    def test_cycle_detection_is_hard_error(self):
        """Cycle in parent chain → hard error."""
        g = HierarchyGraph()
        e1 = _entity("A", "LGD", "LGD_A", EntityType.DISTRICT, 2)
        e2 = _entity("B", "LGD", "LGD_B", EntityType.DISTRICT, 2)
        e1.parent_id = e2.id
        e2.parent_id = e1.id
        g.add_entity(e1)
        g.add_entity(e2)
        hard_errors, warnings = g.resolve_ancestors()
        assert any("CYCLE" in e for e in hard_errors)

    def test_historical_crosswalk_preserves_census_parent(self):
        """Scenario C (valid historical link): crosswalk updates parent_id but keeps census parent in metadata."""
        g, state, district, _ = self._build_basic_graph()
        # Census entity with historical parent
        census_ent = _entity("Narayanpur", "CENSUS_2011", "CEN_NRP", EntityType.CENSUS_TOWN, 4)
        census_ent.metadata = {"historical_census_parent": "OLD_CENSUS_TEHSIL_CODE"}
        g.add_entity(census_ent)

        g.apply_lgd_crosswalk(census_ent, district.id)

        assert census_ent.parent_id == district.id, "Crosswalk must update primary parent_id to LGD parent"
        assert census_ent.metadata.get("census_parent_source_id") == "OLD_CENSUS_TEHSIL_CODE", (
            "Original Census parent source_id must be preserved in metadata"
        )
        assert census_ent.metadata.get("lgd_crosswalk_applied") is True

    def test_historical_census_parent_without_crosswalk_is_not_an_error(self):
        """Scenario C (no crosswalk): Census entity with no LGD crosswalk and unresolved Census parent → warning only."""
        g = HierarchyGraph()
        state = _entity("West Bengal", "LGD", "LGD_WB", EntityType.STATE_UT, 1)
        g.add_entity(state)
        # Census entity whose historical parent code doesn't map to any known entity
        census_ent = _entity("Gobindapur", "CENSUS_2011", "CEN_GDP", EntityType.VILLAGE, 4)
        census_ent.metadata = {
            "historical_census_parent": "CEN2011_WB_OLD_TEHSIL_DEFUNCT",
            "lgd_crosswalk_parent_id": None,
        }
        # No parent_id set — unresolved historical parent
        g.add_entity(census_ent)
        hard_errors, warnings = g.resolve_ancestors()
        # The entity has no parent_id, so no traversal occurs → no hard error
        assert not any(census_ent.name in e for e in hard_errors), (
            "An unresolved historical Census parent without a set parent_id must NOT be a hard error"
        )

    def test_get_all_entities_is_sorted(self):
        g, state, district, village = self._build_basic_graph()
        entities = g.get_all_entities()
        keys = [(e.source or "", e.source_id or "") for e in entities]
        assert keys == sorted(keys), "get_all_entities must return entities in deterministic sorted order"
