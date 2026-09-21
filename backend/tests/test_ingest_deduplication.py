"""Tests for deduplication logic and homonym preservation."""

import pytest

from backend.scripts.ingest.deduplicate import are_true_duplicates, deduplicate_entities
from backend.scripts.ingest.schema import EntityCategory, EntityType, GeographicEntity


def _make_entity(**kwargs) -> GeographicEntity:
    """Helper: create a minimal GeographicEntity with safe defaults."""
    defaults = dict(
        name="TestPlace",
        normalized_name="testplace",
        entity_category=EntityCategory.SETTLEMENT,
        entity_type=EntityType.VILLAGE,
        admin_level=4,
        source="LGD",
        source_id="LGD_001",
        retrieved_at="2024-01-01T00:00:00+00:00",
        country_code="IN",
        state_id="STATE_UP",
        district_id="DIST_UP_A",
        subdistrict_id=None,
        latitude=None,
        longitude=None,
    )
    defaults.update(kwargs)
    e = GeographicEntity(
        name=defaults["name"],
        normalized_name=defaults["normalized_name"],
        entity_category=defaults["entity_category"],
        entity_type=defaults["entity_type"],
        admin_level=defaults["admin_level"],
        source=defaults["source"],
        source_id=defaults["source_id"],
        retrieved_at=defaults["retrieved_at"],
    )
    for k, v in defaults.items():
        if hasattr(e, k) and k not in ("name", "normalized_name", "entity_category",
                                        "entity_type", "admin_level", "source",
                                        "source_id", "retrieved_at"):
            setattr(e, k, v)
    return e


# ---------------------------------------------------------------------------
# are_true_duplicates
# ---------------------------------------------------------------------------

class TestAreTrueDuplicates:

    def test_same_source_and_source_id_is_duplicate(self):
        e1 = _make_entity(source_id="LGD_SAME")
        e2 = _make_entity(source_id="LGD_SAME")
        assert are_true_duplicates(e1, e2)

    def test_different_normalized_name_not_duplicate(self):
        e1 = _make_entity(normalized_name="rampur")
        e2 = _make_entity(normalized_name="ramnagar")
        assert not are_true_duplicates(e1, e2)

    def test_different_entity_type_not_duplicate(self):
        """VILLAGE and STATUTORY_TOWN are never merged even if names match."""
        e1 = _make_entity(entity_type=EntityType.VILLAGE, source_id="SAME_CODE")
        e2 = _make_entity(entity_type=EntityType.STATUTORY_TOWN, source_id="SAME_CODE")
        assert not are_true_duplicates(e1, e2)

    def test_different_states_not_duplicate(self):
        """Scenario A: same name in different states must never be merged."""
        e1 = _make_entity(normalized_name="rampur", state_id="STATE_UP", district_id="DIST_UP_X", source_id="ID_UP")
        e2 = _make_entity(normalized_name="rampur", state_id="STATE_HP", district_id="DIST_HP_Y", source_id="ID_HP")
        assert not are_true_duplicates(e1, e2)

    def test_same_state_different_districts_not_duplicate(self):
        """Scenario B: same name, same state, different districts → homonym, not duplicate."""
        e1 = _make_entity(normalized_name="krishnapur", state_id="STATE_WB",
                           district_id="DIST_WB_HOWRAH", source_id="ID_HWR")
        e2 = _make_entity(normalized_name="krishnapur", state_id="STATE_WB",
                           district_id="DIST_WB_HOOGHLY", source_id="ID_HGL")
        assert not are_true_duplicates(e1, e2)

    def test_same_district_different_subdistricts_not_duplicate(self):
        e1 = _make_entity(normalized_name="nagar", subdistrict_id="SD_001", source_id="S1")
        e2 = _make_entity(normalized_name="nagar", subdistrict_id="SD_002", source_id="S2")
        assert not are_true_duplicates(e1, e2)

    def test_spatial_proximity_triggers_merge(self):
        """Two entities with the same name, same hierarchy, nearby coords → duplicate."""
        e1 = _make_entity(normalized_name="smalltown", source_id="ID_A",
                           latitude=22.5726, longitude=88.3639)
        e2 = _make_entity(normalized_name="smalltown", source_id="ID_B",
                           latitude=22.5730, longitude=88.3645)  # ~50 m away
        assert are_true_duplicates(e1, e2)

    def test_spatial_far_apart_not_duplicate(self):
        """Same name, same hierarchy, but > 5 km apart → not a duplicate."""
        e1 = _make_entity(normalized_name="durgapur", source_id="ID_X",
                           latitude=23.5204, longitude=87.3119)
        e2 = _make_entity(normalized_name="durgapur", source_id="ID_Y",
                           latitude=23.9000, longitude=87.5000)  # > 50 km away
        assert not are_true_duplicates(e1, e2)

    def test_identical_source_id_different_source_not_duplicate(self):
        """Same source_id string but different source → NOT a definitive duplicate."""
        e1 = _make_entity(source="LGD", source_id="SHARED_CODE")
        e2 = _make_entity(source="CENSUS_2011", source_id="SHARED_CODE")
        # No coordinates → cannot confirm via proximity either
        # Result: not confirmed duplicate (different source system)
        # This passes because are_true_duplicates checks source == source AND source_id
        assert not are_true_duplicates(e1, e2)


# ---------------------------------------------------------------------------
# deduplicate_entities
# ---------------------------------------------------------------------------

class TestDeduplicateEntities:

    def test_scenario_a_homonyms_different_states_preserved(self):
        """Scenario A: Rampur in UP and Rampur in HP must both survive."""
        e1 = _make_entity(name="Rampur", normalized_name="rampur", state_id="STATE_UP",
                           district_id="DIST_UP_R", source_id="LGD_UP_R")
        e2 = _make_entity(name="Rampur", normalized_name="rampur", state_id="STATE_HP",
                           district_id="DIST_HP_R", source_id="LGD_HP_R")
        result, log = deduplicate_entities([e1, e2])
        assert len(result) == 2, "Homonyms in different states must both be preserved"

    def test_scenario_b_homonyms_same_state_different_district_preserved(self):
        """Scenario B: Krishnapur in Howrah and Krishnapur in Hooghly → 2 entities."""
        e1 = _make_entity(name="Krishnapur", normalized_name="krishnapur", state_id="STATE_WB",
                           district_id="DIST_WB_HOWRAH", source_id="LGD_KPR_H")
        e2 = _make_entity(name="Krishnapur", normalized_name="krishnapur", state_id="STATE_WB",
                           district_id="DIST_WB_HOOGHLY", source_id="LGD_KPR_G")
        result, log = deduplicate_entities([e1, e2])
        assert len(result) == 2, "Homonyms in different districts must both be preserved"

    def test_scenario_j_exact_source_id_merged(self):
        """Scenario J: Identical source + source_id → merged to 1 entity."""
        e1 = _make_entity(name="Kolkata", normalized_name="kolkata",
                           entity_type=EntityType.STATUTORY_TOWN,
                           state_id="STATE_WB", district_id="DIST_WB_KOL",
                           source="LGD", source_id="LGD_WB_KOLKATA_MC",
                           latitude=22.5726, longitude=88.3639)
        e2 = _make_entity(name="Kolkata", normalized_name="kolkata",
                           entity_type=EntityType.STATUTORY_TOWN,
                           state_id="STATE_WB", district_id="DIST_WB_KOL",
                           source="LGD", source_id="LGD_WB_KOLKATA_MC",
                           latitude=22.5726, longitude=88.3639)
        result, log = deduplicate_entities([e1, e2])
        assert len(result) == 1, "Exact source+source_id duplicate must be merged"
        assert any("MERGE" in line for line in log)

    def test_different_entity_types_not_merged(self):
        """A VILLAGE and a STATUTORY_TOWN with the same name must never merge."""
        e1 = _make_entity(normalized_name="nagar",
                           entity_type=EntityType.VILLAGE, source_id="VIL_001")
        e2 = _make_entity(normalized_name="nagar",
                           entity_type=EntityType.STATUTORY_TOWN, source_id="VIL_001")
        result, log = deduplicate_entities([e1, e2])
        assert len(result) == 2

    def test_output_is_deterministic(self):
        """Running deduplication twice on the same input yields the same result."""
        entities = [
            _make_entity(name="X", normalized_name="x", source_id=f"ID_{i}")
            for i in range(5)
        ]
        r1, _ = deduplicate_entities(entities)
        r2, _ = deduplicate_entities(entities)
        assert [e.id for e in r1] == [e.id for e in r2]
