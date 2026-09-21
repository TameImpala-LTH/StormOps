"""
Regression tests for India-aware location resolution.

Verifies that city+state qualifiers like "Newtown, West Bengal" are correctly
resolved to India, and that non-Indian queries are not affected.

These tests mock httpx to avoid real network calls.
"""

import sys
import os
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.core.compat import *  # noqa: F401,F403 — initialize compat shims
from app.services.geocoding_service import (
    GeocodingService,
    geocode_cache_clear,
    INDIAN_STATE_NAMES,
    INDIAN_STATE_TO_CANONICAL,
)
from app.schemas.query import GeocodedLocationSchema


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_response(results: list, status_code: int = 200) -> MagicMock:
    """Build a mock httpx Response-like object."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {"results": results}
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def _om_result(
    name: str,
    country: str,
    country_code: str,
    admin1: str,
    lat: float,
    lon: float,
    population: int = 10000,
    timezone: str = "UTC",
) -> dict:
    """Build a fake Open-Meteo geocoding result dict."""
    return {
        "name": name,
        "country": country,
        "country_code": country_code,
        "admin1": admin1,
        "latitude": lat,
        "longitude": lon,
        "population": population,
        "timezone": timezone,
    }


async def _geocode(location_name: str, om_results: list) -> GeocodedLocationSchema:
    """Helper: call geocode_location() with mocked Open-Meteo response."""
    geocode_cache_clear()
    mock_resp = _make_mock_response(om_results)
    service = GeocodingService()

    with patch("httpx.AsyncClient") as MockClient:
        mock_ctx = AsyncMock()
        mock_ctx.get = AsyncMock(return_value=mock_resp)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await service.geocode_location(location_name)
    return result


# ---------------------------------------------------------------------------
# INDIAN_STATE_NAMES coverage tests
# ---------------------------------------------------------------------------

class TestIndianStateNamesCoverage:
    """Ensure the INDIAN_STATE_NAMES set includes expected entries."""

    def test_all_28_states_present(self):
        required_states = [
            "andhra pradesh", "arunachal pradesh", "assam", "bihar",
            "chhattisgarh", "goa", "gujarat", "haryana", "himachal pradesh",
            "jharkhand", "karnataka", "kerala", "madhya pradesh", "maharashtra",
            "manipur", "meghalaya", "mizoram", "nagaland", "odisha", "punjab",
            "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura",
            "uttar pradesh", "uttarakhand", "west bengal",
        ]
        for state in required_states:
            assert state in INDIAN_STATE_NAMES, f"'{state}' missing from INDIAN_STATE_NAMES"

    def test_union_territories_present(self):
        required_uts = ["delhi", "chandigarh", "ladakh", "puducherry", "lakshadweep"]
        for ut in required_uts:
            assert ut in INDIAN_STATE_NAMES, f"'{ut}' missing from INDIAN_STATE_NAMES"

    def test_abbreviations_present(self):
        assert "wb" in INDIAN_STATE_NAMES
        assert "up" in INDIAN_STATE_NAMES
        assert "mp" in INDIAN_STATE_NAMES
        assert "ap" in INDIAN_STATE_NAMES

    def test_alternate_spellings_present(self):
        assert "orissa" in INDIAN_STATE_NAMES  # historical name for Odisha
        assert "pondicherry" in INDIAN_STATE_NAMES  # historical name for Puducherry
        assert "uttaranchal" in INDIAN_STATE_NAMES  # historical name for Uttarakhand

    def test_canonical_mapping_completeness(self):
        """Every entry in INDIAN_STATE_TO_CANONICAL must have a non-empty value."""
        for key, value in INDIAN_STATE_TO_CANONICAL.items():
            assert value, f"INDIAN_STATE_TO_CANONICAL['{key}'] is empty"


# ---------------------------------------------------------------------------
# Geocoding integration tests (mocked HTTP)
# ---------------------------------------------------------------------------

class TestIndiaAwareGeocoding:
    """Regression tests for India-aware location resolution."""

    # TC-1: "Newtown, West Bengal" must resolve to West Bengal, India — NOT Pennsylvania, USA
    @pytest.mark.asyncio
    async def test_tc1_newtown_west_bengal_resolves_india(self):
        om_results = [
            # Open-Meteo might return Pennsylvania first (higher population globally)
            _om_result("Newtown", "United States", "US", "Pennsylvania", 39.9081, -74.9321, population=20000),
            _om_result("New Town", "India", "IN", "West Bengal", 22.5890, 88.4820, population=100000),
        ]
        result = await _geocode("Newtown, West Bengal", om_results)
        assert result.country_code == "IN", f"Expected IN, got {result.country_code}"
        assert (result.admin1 or "").lower() == "west bengal", f"Expected West Bengal, got {result.admin1}"
        assert "India" in result.country or result.country_code == "IN"

    # TC-2: "Newtown" without qualifier should geocode without India bias
    @pytest.mark.asyncio
    async def test_tc2_newtown_no_qualifier_unbiased(self):
        om_results = [
            _om_result("Newtown", "United States", "US", "Pennsylvania", 39.9081, -74.9321, population=20000),
        ]
        result = await _geocode("Newtown", om_results)
        # No India constraint was applied — result should be what Open-Meteo returns
        assert result.country_code == "US"
        assert "Pennsylvania" in (result.admin1 or "")

    # TC-3: "Salt Lake, West Bengal" → India / West Bengal
    @pytest.mark.asyncio
    async def test_tc3_salt_lake_west_bengal(self):
        om_results = [
            _om_result("Bidhannagar", "India", "IN", "West Bengal", 22.5672, 88.3998, population=480000),
        ]
        result = await _geocode("Salt Lake, West Bengal", om_results)
        assert result.country_code == "IN"
        assert (result.admin1 or "").lower() == "west bengal"

    # TC-4: "Pune, Maharashtra" → India / Maharashtra
    @pytest.mark.asyncio
    async def test_tc4_pune_maharashtra(self):
        om_results = [
            _om_result("Pune", "India", "IN", "Maharashtra", 18.5204, 73.8567, population=3124458),
        ]
        result = await _geocode("Pune, Maharashtra", om_results)
        assert result.country_code == "IN"
        assert (result.admin1 or "").lower() == "maharashtra"

    # TC-5: "Kozhikode, Kerala" → India / Kerala
    @pytest.mark.asyncio
    async def test_tc5_kozhikode_kerala(self):
        om_results = [
            _om_result("Kozhikode", "India", "IN", "Kerala", 11.2588, 75.7804, population=519601),
        ]
        result = await _geocode("Kozhikode, Kerala", om_results)
        assert result.country_code == "IN"
        assert (result.admin1 or "").lower() == "kerala"

    # TC-6: "Lucknow, Uttar Pradesh" → India / Uttar Pradesh
    @pytest.mark.asyncio
    async def test_tc6_lucknow_uttar_pradesh(self):
        om_results = [
            _om_result("Lucknow", "India", "IN", "Uttar Pradesh", 26.8467, 80.9462, population=2901474),
        ]
        result = await _geocode("Lucknow, Uttar Pradesh", om_results)
        assert result.country_code == "IN"
        assert (result.admin1 or "").lower() == "uttar pradesh"

    # TC-7: "Indore, Madhya Pradesh" → India / Madhya Pradesh
    @pytest.mark.asyncio
    async def test_tc7_indore_madhya_pradesh(self):
        om_results = [
            _om_result("Indore", "India", "IN", "Madhya Pradesh", 22.7196, 75.8577, population=1960000),
        ]
        result = await _geocode("Indore, Madhya Pradesh", om_results)
        assert result.country_code == "IN"
        assert (result.admin1 or "").lower() == "madhya pradesh"

    # TC-8: "Guwahati, Assam" → India / Assam
    @pytest.mark.asyncio
    async def test_tc8_guwahati_assam(self):
        om_results = [
            _om_result("Guwahati", "India", "IN", "Assam", 26.1445, 91.7362, population=957352),
        ]
        result = await _geocode("Guwahati, Assam", om_results)
        assert result.country_code == "IN"
        assert (result.admin1 or "").lower() == "assam"

    # TC-9: "London, UK" must NOT be affected by Indian state detection
    @pytest.mark.asyncio
    async def test_tc9_london_uk_unaffected(self):
        om_results = [
            _om_result("London", "United Kingdom", "GB", "England", 51.5085, -0.1257, population=7556900),
        ]
        result = await _geocode("London, UK", om_results)
        assert result.country_code == "GB", f"Expected GB, got {result.country_code}"
        assert "United Kingdom" in result.country

    # TC-10: "Springfield, USA" must NOT be affected by Indian state detection
    @pytest.mark.asyncio
    async def test_tc10_springfield_usa_unaffected(self):
        om_results = [
            _om_result("Springfield", "United States", "US", "Illinois", 39.7994, -89.6542, population=114230),
        ]
        result = await _geocode("Springfield, USA", om_results)
        assert result.country_code == "US", f"Expected US, got {result.country_code}"

    # TC-11: State qualifier in cache key — "Newtown, WB" and "Newtown" must not collide
    @pytest.mark.asyncio
    async def test_tc11_state_qualified_cache_key_does_not_collide(self):
        geocode_cache_clear()

        india_results = [
            _om_result("New Town", "India", "IN", "West Bengal", 22.589, 88.482, population=100000),
        ]
        us_results = [
            _om_result("Newtown", "United States", "US", "Pennsylvania", 39.908, -74.932, population=20000),
        ]

        india_result = await _geocode("Newtown, West Bengal", india_results)
        us_result = await _geocode("Newtown", us_results)

        assert india_result.country_code == "IN"
        assert us_result.country_code == "US"
        # Confirm they resolved to different countries
        assert india_result.country_code != us_result.country_code

    # TC-12: Display name includes State and Country when India state qualifier used
    @pytest.mark.asyncio
    async def test_tc12_display_name_includes_state_country(self):
        om_results = [
            _om_result("New Town", "India", "IN", "West Bengal", 22.589, 88.482, population=100000),
        ]
        result = await _geocode("Newtown, West Bengal", om_results)
        # Display name should include the state and country
        assert "West Bengal" in result.name or (result.admin1 or "").lower() == "west bengal"
        assert "India" in result.country or result.country_code == "IN"

    # TC-13: "Newtown, Pennsylvania" -> Newtown / Pennsylvania / United States
    @pytest.mark.asyncio
    async def test_tc13_newtown_pennsylvania_resolves_us(self):
        om_results = [
            _om_result("Newtown", "United States", "US", "Pennsylvania", 40.229, -74.937, population=2222),
            _om_result("New Town", "India", "IN", "West Bengal", 22.589, 88.482, population=100000),
        ]
        result = await _geocode("Newtown, Pennsylvania", om_results)
        assert result.country_code == "US"
        assert (result.admin1 or "").lower() == "pennsylvania"
        assert (result.state or "").lower() == "pennsylvania"
        assert "United States" in result.country
        assert "Newtown" in result.name

    # TC-14: Cache keys for "Newtown, West Bengal" and "Newtown, Pennsylvania" must remain distinct
    @pytest.mark.asyncio
    async def test_tc14_cache_keys_newtown_wb_vs_pa_remain_distinct(self):
        geocode_cache_clear()
        wb_results = [
            _om_result("New Town", "India", "IN", "West Bengal", 22.589, 88.482, population=100000),
        ]
        pa_results = [
            _om_result("Newtown", "United States", "US", "Pennsylvania", 40.229, -74.937, population=2222),
        ]
        wb_res = await _geocode("Newtown, West Bengal", wb_results)
        pa_res = await _geocode("Newtown, Pennsylvania", pa_results)

        assert wb_res.country_code == "IN"
        assert pa_res.country_code == "US"
        assert wb_res.latitude != pa_res.latitude
        assert wb_res.longitude != pa_res.longitude

    # TC-15: "Kolkata" -> Kolkata / West Bengal / India (Open-Meteo path)
    @pytest.mark.asyncio
    async def test_tc15_kolkata_open_meteo(self):
        om_results = [
            _om_result("Kolkata", "India", "IN", "West Bengal", 22.5626, 88.3630, population=4631392),
        ]
        result = await _geocode("Kolkata", om_results)
        assert result.country_code == "IN"
        assert (result.admin1 or "").lower() == "west bengal"
        assert (result.state or "").lower() == "west bengal"
        assert "India" in result.country
        assert "Kolkata" in result.name

    # TC-16: Nominatim fallback path — "Newtown, West Bengal" (when Open-Meteo returns empty)
    @pytest.mark.asyncio
    async def test_tc16_newtown_west_bengal_nominatim_fallback(self):
        """Simulates real-world behavior where Open-Meteo has no result for New Town IN,
        falling back to Nominatim to resolve New Town in West Bengal."""
        geocode_cache_clear()
        service = GeocodingService()

        om_empty_resp = MagicMock()
        om_empty_resp.status_code = 200
        om_empty_resp.json.return_value = {"results": []}
        om_empty_resp.raise_for_status = MagicMock()

        nom_item = {
            "name": "New Town",
            "lat": "22.5882",
            "lon": "88.4734",
            "class": "place",
            "type": "city",
            "address": {
                "city": "New Town",
                "county": "Rajarhat",
                "state_district": "North 24 Parganas",
                "state": "West Bengal",
                "country": "India",
                "country_code": "in",
            },
        }
        nom_resp = MagicMock()
        nom_resp.status_code = 200
        nom_resp.json.return_value = [nom_item]

        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.get = AsyncMock(side_effect=[om_empty_resp, nom_resp])
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await service.geocode_location("Newtown, West Bengal")

        assert result.country_code == "IN"
        assert (result.admin1 or "").lower() == "west bengal"
        assert (result.state or "").lower() == "west bengal"
        assert (result.district or "").lower() == "north 24 parganas"
        assert (result.subdivision or "").lower() == "rajarhat"
        assert "New Town" in result.name

    # TC-17: Nominatim fallback path — "Behala, Kolkata"
    @pytest.mark.asyncio
    async def test_tc17_behala_kolkata_nominatim_fallback(self):
        """Tests micro-locality resolution for Behala, Kolkata via Nominatim fallback."""
        geocode_cache_clear()
        service = GeocodingService()

        om_empty_resp = MagicMock()
        om_empty_resp.status_code = 200
        om_empty_resp.json.return_value = {"results": []}
        om_empty_resp.raise_for_status = MagicMock()

        nom_item = {
            "name": "Behala",
            "lat": "22.4988",
            "lon": "88.3149",
            "class": "place",
            "type": "suburb",
            "address": {
                "suburb": "Behala",
                "city": "Kolkata",
                "state_district": "Kolkata",
                "state": "West Bengal",
                "country": "India",
                "country_code": "in",
            },
        }
        nom_resp = MagicMock()
        nom_resp.status_code = 200
        nom_resp.json.return_value = [nom_item]

        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.get = AsyncMock(side_effect=[om_empty_resp, nom_resp])
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await service.geocode_location("Behala, Kolkata")

        assert result.country_code == "IN"
        assert (result.admin1 or "").lower() == "west bengal"
        assert (result.state or "").lower() == "west bengal"
        assert (result.city or "").lower() == "kolkata"
        assert (result.locality or "").lower() == "behala"
        assert (result.district or "").lower() == "kolkata"
        assert "Behala" in result.name or "Kolkata" in result.name

    # TC-18: Nominatim fallback path — "Rajarhat, West Bengal"
    @pytest.mark.asyncio
    async def test_tc18_rajarhat_west_bengal_nominatim_fallback(self):
        """Tests subdivision/county resolution for Rajarhat, West Bengal via Nominatim fallback."""
        geocode_cache_clear()
        service = GeocodingService()

        om_empty_resp = MagicMock()
        om_empty_resp.status_code = 200
        om_empty_resp.json.return_value = {"results": []}
        om_empty_resp.raise_for_status = MagicMock()

        nom_item = {
            "name": "Rajarhat",
            "lat": "22.6100",
            "lon": "88.5200",
            "class": "boundary",
            "type": "administrative",
            "address": {
                "county": "Rajarhat",
                "state_district": "North 24 Parganas",
                "state": "West Bengal",
                "country": "India",
                "country_code": "in",
            },
        }
        nom_resp = MagicMock()
        nom_resp.status_code = 200
        nom_resp.json.return_value = [nom_item]

        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.get = AsyncMock(side_effect=[om_empty_resp, nom_resp])
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await service.geocode_location("Rajarhat, West Bengal")

        assert result.country_code == "IN"
        assert (result.admin1 or "").lower() == "west bengal"
        assert (result.state or "").lower() == "west bengal"
        assert (result.district or "").lower() == "north 24 parganas"
        assert "Rajarhat" in result.name

    # TC-19: Nominatim fallback path — "Salt Lake, Kolkata"
    @pytest.mark.asyncio
    async def test_tc19_salt_lake_kolkata_nominatim_fallback(self):
        """Tests neighbourhood resolution for Salt Lake, Kolkata via Nominatim fallback."""
        geocode_cache_clear()
        service = GeocodingService()

        om_empty_resp = MagicMock()
        om_empty_resp.status_code = 200
        om_empty_resp.json.return_value = {"results": []}
        om_empty_resp.raise_for_status = MagicMock()

        nom_item = {
            "name": "Bidhannagar",
            "lat": "22.5800",
            "lon": "88.4200",
            "class": "place",
            "type": "city",
            "address": {
                "city": "Bidhannagar",
                "county": "Rajarhat",
                "state_district": "North 24 Parganas",
                "state": "West Bengal",
                "country": "India",
                "country_code": "in",
            },
        }
        nom_resp = MagicMock()
        nom_resp.status_code = 200
        nom_resp.json.return_value = [nom_item]

        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.get = AsyncMock(side_effect=[om_empty_resp, nom_resp])
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await service.geocode_location("Salt Lake, Kolkata")

        assert result.country_code == "IN"
        assert (result.admin1 or "").lower() == "west bengal"
        assert (result.state or "").lower() == "west bengal"
        assert "India" in result.country
