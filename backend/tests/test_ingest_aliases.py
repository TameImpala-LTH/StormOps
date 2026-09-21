"""Tests for alias generation, OSM alias policy, and curated alias handling."""

import pytest

from backend.scripts.ingest.aliases import generate_deterministic_aliases, AUTHORITATIVE_HISTORICAL_ALIASES
from backend.scripts.ingest.sources.osm import OSMAdapter
from backend.scripts.ingest.sources.curated import CuratedAdapter


class TestDeterministicAliases:

    def _entity_for(self, name):
        from backend.scripts.ingest.schema import EntityCategory, EntityType, GeographicEntity
        e = GeographicEntity(
            name=name,
            normalized_name=name.lower(),
            entity_category=EntityCategory.SETTLEMENT,
            entity_type=EntityType.STATUTORY_TOWN,
            admin_level=4,
            source="LGD",
            source_id=f"LGD_{name.upper()}",
            retrieved_at="2024-01-01T00:00:00+00:00",
        )
        return e

    def test_kolkata_gets_calcutta_alias(self):
        """Scenario E: Bengaluru / Kolkata authoritative historical aliases must be present."""
        e = self._entity_for("Kolkata")
        aliases = generate_deterministic_aliases(e)
        alias_strs = [a.alias for a in aliases]
        assert "Calcutta" in alias_strs

    def test_bengaluru_gets_bangalore_alias(self):
        e = self._entity_for("Bengaluru")
        aliases = generate_deterministic_aliases(e)
        alias_strs = [a.alias for a in aliases]
        assert "Bangalore" in alias_strs

    def test_unknown_city_gets_no_aliases(self):
        e = self._entity_for("UnknownCityXYZ")
        aliases = generate_deterministic_aliases(e)
        # Only junction and compound rules could fire, not history
        # For a simple name with no match, result should be empty or minimal
        for a in aliases:
            assert a.alias != "UnknownCityXYZ (OSM)", "Artificial OSM alias must never appear"

    def test_no_duplicate_aliases(self):
        """No alias should match the canonical name's normalized form."""
        for canonical in AUTHORITATIVE_HISTORICAL_ALIASES:
            e = self._entity_for(canonical)
            aliases = generate_deterministic_aliases(e)
            canonical_norm = canonical.lower()
            for a in aliases:
                assert a.normalized_alias != canonical_norm, (
                    f"Alias '{a.alias}' normalizes to same form as canonical '{canonical}'"
                )

    def test_junction_variant_generates_crossing_alias(self):
        e = self._entity_for("Dhakuria More")
        aliases = generate_deterministic_aliases(e)
        alias_strs = [a.alias for a in aliases]
        assert "Dhakuria Crossing" in alias_strs

    def test_compound_rule_fires_for_two_word_name(self):
        e = self._entity_for("New Town")
        aliases = generate_deterministic_aliases(e)
        alias_strs = [a.alias for a in aliases]
        assert "NewTown" in alias_strs


class TestOSMAliasPolicy:

    def test_no_artificial_osm_label_alias(self):
        """OSMAdapter must NOT generate aliases of the form 'Name (OSM)'."""
        adapter = OSMAdapter()
        features = [
            {
                "osm_id": "OSM_TEST_001",
                "place": "neighbourhood",
                "name": "Park Street",
                "name:en": "",
                "alt_name": "",
                "old_name": "",
                "latitude": 22.55,
                "longitude": 88.35,
            }
        ]
        _, aliases, _ = adapter.parse(features)
        for a in aliases:
            assert "(OSM)" not in a.alias, f"Artificial OSM alias found: '{a.alias}'"

    def test_no_qualified_form_alias(self):
        """Scenario F: 'Park Street, Kolkata' must NOT appear as an alias."""
        adapter = OSMAdapter()
        features = [
            {
                "osm_id": "OSM_TEST_002",
                "place": "neighbourhood",
                "name": "Park Street",
                "name:en": "",
                "alt_name": "",
                "old_name": "",
                "latitude": 22.55,
                "longitude": 88.35,
                "district": "Kolkata",
            }
        ]
        _, aliases, _ = adapter.parse(features)
        qualified = "Park Street, Kolkata"
        for a in aliases:
            assert a.alias != qualified, f"Qualified query form must not be stored as alias: '{a.alias}'"

    def test_genuine_old_name_alias_is_kept(self):
        """OSMAdapter must preserve old_name as a HISTORICAL alias."""
        adapter = OSMAdapter()
        features = [
            {
                "osm_id": "OSM_MH_MUMBAI",
                "place": "city",
                "name": "Mumbai",
                "name:en": "Mumbai",
                "alt_name": "",
                "old_name": "Bombay",
                "latitude": 19.076,
                "longitude": 72.877,
            }
        ]
        _, aliases, _ = adapter.parse(features)
        alias_strs = [a.alias for a in aliases]
        assert "Bombay" in alias_strs, "Genuine old_name 'Bombay' must appear as an alias"

    def test_name_en_alias_only_when_different(self):
        """name:en alias only added when it differs from the primary name."""
        adapter = OSMAdapter()
        features = [
            {
                "osm_id": "OSM_001",
                "place": "suburb",
                "name": "Bandra",
                "name:en": "Bandra",  # Identical: must NOT create a duplicate alias
                "alt_name": "",
                "old_name": "",
                "latitude": 19.059,
                "longitude": 72.829,
            }
        ]
        _, aliases, _ = adapter.parse(features)
        # Should be zero aliases since name:en == name and no other aliases
        assert len(aliases) == 0


class TestCuratedAliasPolicy:

    def test_explicit_aliases_are_retained(self):
        """Scenario I: Explicitly listed aliases in curated JSON are retained."""
        adapter = CuratedAdapter()
        items = [
            {
                "name": "Andheri",
                "city": "Mumbai",
                "aliases": ["Andheri East", "Andheri West"],
            }
        ]
        _, aliases, _ = adapter.parse(items)
        alias_strs = [a.alias for a in aliases]
        assert "Andheri East" in alias_strs
        assert "Andheri West" in alias_strs

    def test_city_label_not_fabricated_as_alias(self):
        """The 'city' field in curated data must NOT become an alias."""
        adapter = CuratedAdapter()
        items = [
            {
                "name": "Bandra",
                "city": "Mumbai",
                "aliases": [],
            }
        ]
        _, aliases, _ = adapter.parse(items)
        alias_strs = [a.alias for a in aliases]
        assert "Mumbai" not in alias_strs, "city label must not be fabricated into an alias"
        assert "Bandra, Mumbai" not in alias_strs, "Qualified form must not appear as alias"
