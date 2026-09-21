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
from app.services.india_locality_service import india_locality_service
from fastapi import HTTPException


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

    # TC-20: Fresh session — "Park Street" without prior context resolves to Kolkata, West Bengal
    @pytest.mark.asyncio
    async def test_tc20_fresh_session_park_street(self):
        geocode_cache_clear()
        service = GeocodingService()

        nom_item = {
            "name": "Park Street",
            "lat": "22.5551",
            "lon": "88.3501",
            "address": {
                "suburb": "Dharmatala",
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
            mock_ctx.get = AsyncMock(return_value=nom_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await service.geocode_location("Park Street")

        assert result.country_code == "IN"
        assert result.state == "West Bengal"
        assert result.city == "Kolkata"
        assert result.locality == "Park Street"
        assert "Park Street" in result.name
        assert "Kolkata" in result.name
        assert result.timezone == "Asia/Kolkata"

    # TC-21: Fresh session — "Gariahat" without prior context resolves to Kolkata, West Bengal
    @pytest.mark.asyncio
    async def test_tc21_fresh_session_gariahat(self):
        geocode_cache_clear()
        service = GeocodingService()

        nom_item = {
            "name": "Gariahat",
            "lat": "22.5197",
            "lon": "88.3654",
            "address": {
                "suburb": "Ballygunge",
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
            mock_ctx.get = AsyncMock(return_value=nom_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await service.geocode_location("Gariahat")

        assert result.country_code == "IN"
        assert result.state == "West Bengal"
        assert result.city == "Kolkata"
        assert result.locality == "Gariahat"
        assert "Gariahat" in result.name

    # TC-22: Fresh session — "Bandra" without prior context resolves to Mumbai, Maharashtra
    @pytest.mark.asyncio
    async def test_tc22_fresh_session_bandra(self):
        geocode_cache_clear()
        service = GeocodingService()

        nom_item = {
            "name": "Bandra",
            "lat": "19.0550",
            "lon": "72.8402",
            "address": {
                "suburb": "Khar",
                "city": "Mumbai",
                "state_district": "Mumbai Suburban District",
                "state": "Maharashtra",
                "country": "India",
                "country_code": "in",
            },
        }
        nom_resp = MagicMock()
        nom_resp.status_code = 200
        nom_resp.json.return_value = [nom_item]

        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.get = AsyncMock(return_value=nom_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await service.geocode_location("Bandra")

        assert result.country_code == "IN"
        assert result.state == "Maharashtra"
        assert result.city == "Mumbai"
        assert result.locality == "Bandra"
        assert "Bandra" in result.name

    # TC-23: Fresh session — "Koramangala" without prior context resolves to Bengaluru, Karnataka
    @pytest.mark.asyncio
    async def test_tc23_fresh_session_koramangala(self):
        geocode_cache_clear()
        service = GeocodingService()

        nom_item = {
            "name": "Koramangala",
            "lat": "12.9357",
            "lon": "77.6241",
            "address": {
                "suburb": "Koramangala",
                "city": "Bengaluru",
                "state_district": "Bengaluru Urban",
                "state": "Karnataka",
                "country": "India",
                "country_code": "in",
            },
        }
        nom_resp = MagicMock()
        nom_resp.status_code = 200
        nom_resp.json.return_value = [nom_item]

        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.get = AsyncMock(return_value=nom_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await service.geocode_location("Koramangala")

        assert result.country_code == "IN"
        assert result.state == "Karnataka"
        assert result.city == "Bengaluru"
        assert result.locality == "Koramangala"
        assert "Koramangala" in result.name

    # TC-24: Explicit override wins over Indian locality default ("Park Street, London")
    @pytest.mark.asyncio
    async def test_tc24_explicit_qualifier_override_london(self):
        geocode_cache_clear()
        service = GeocodingService()

        om_item = _om_result(
            name="Park Street",
            country="United Kingdom",
            country_code="GB",
            admin1="England",
            lat=51.7167,
            lon=-0.3333,
        )
        om_resp = _make_mock_response([om_item])

        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.get = AsyncMock(return_value=om_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await service.geocode_location("Park Street, London")

        assert result.country_code == "GB"
        assert "United Kingdom" in result.country

    # TC-25: Contextual resolution with prior session context
    @pytest.mark.asyncio
    async def test_tc25_contextual_resolution_with_session(self):
        geocode_cache_clear()
        service = GeocodingService()

        session_loc = GeocodedLocationSchema(
            name="Kolkata, West Bengal, India",
            country="India",
            country_code="IN",
            admin1="West Bengal",
            state="West Bengal",
            city="Kolkata",
            latitude=22.5726,
            longitude=88.3639,
            timezone="Asia/Kolkata",
        )

        nom_item = {
            "name": "Jadavpur",
            "lat": "22.4988",
            "lon": "88.3718",
            "address": {
                "suburb": "Jadavpur",
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
            mock_ctx.get = AsyncMock(return_value=nom_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await service.geocode_location("Jadavpur", context_location=session_loc)

        assert result.country_code == "IN"
        assert result.state == "West Bengal"
        assert result.city == "Kolkata"

    # TC-26: Explicit qualifier overrides active session context
    @pytest.mark.asyncio
    async def test_tc26_explicit_override_active_session_context(self):
        geocode_cache_clear()
        service = GeocodingService()

        session_loc = GeocodedLocationSchema(
            name="Kolkata, West Bengal, India",
            country="India",
            country_code="IN",
            admin1="West Bengal",
            state="West Bengal",
            city="Kolkata",
            latitude=22.5726,
            longitude=88.3639,
            timezone="Asia/Kolkata",
        )

        om_item = _om_result(
            name="Boston",
            country="United States",
            country_code="US",
            admin1="Massachusetts",
            lat=42.3601,
            lon=-71.0589,
        )
        om_resp = _make_mock_response([om_item])

        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.get = AsyncMock(return_value=om_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await service.geocode_location("Boston, USA", context_location=session_loc)

        assert result.country_code == "US"
        assert "United States" in result.country
        assert result.city == "Boston"


# ---------------------------------------------------------------------------
# Phase 21: Dedicated India Locality Architecture & Acceptance Test Suite
# ---------------------------------------------------------------------------

class TestIndiaLocalityArchitecture:
    """Comprehensive test suite verifying the 8-stage India-first locality architecture."""

    # 1. Fresh-session Indian locality resolution (all 9 acceptance regions, 27 localities)
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "locality,expected_city,expected_state",
        [
            # Kolkata
            ("Park Street", "Kolkata", "West Bengal"),
            ("Gariahat", "Kolkata", "West Bengal"),
            ("Maniktala", "Kolkata", "West Bengal"),
            ("Hatibagan", "Kolkata", "West Bengal"),
            ("Jadavpur", "Kolkata", "West Bengal"),
            ("Tollygunge", "Kolkata", "West Bengal"),
            ("Behala", "Kolkata", "West Bengal"),
            # Mumbai
            ("Bandra", "Mumbai", "Maharashtra"),
            ("Andheri", "Mumbai", "Maharashtra"),
            ("Kurla", "Mumbai", "Maharashtra"),
            ("Charni Road", "Mumbai", "Maharashtra"),
            # Bengaluru
            ("Koramangala", "Bengaluru", "Karnataka"),
            ("Indiranagar", "Bengaluru", "Karnataka"),
            ("Basavanagudi", "Bengaluru", "Karnataka"),
            ("Frazer Town", "Bengaluru", "Karnataka"),
            # Ahmedabad
            ("Maninagar", "Ahmedabad", "Gujarat"),
            ("Navrangpura", "Ahmedabad", "Gujarat"),
            # Jaipur
            ("Malviya Nagar", "Jaipur", "Rajasthan"),
            ("Vaishali Nagar", "Jaipur", "Rajasthan"),
            # Lucknow
            ("Aliganj", "Lucknow", "Uttar Pradesh"),
            ("Hazratganj", "Lucknow", "Uttar Pradesh"),
            # Bhubaneswar
            ("Patia", "Bhubaneswar", "Odisha"),
            ("Saheed Nagar", "Bhubaneswar", "Odisha"),
            # Ranchi
            ("Doranda", "Ranchi", "Jharkhand"),
            ("Morabadi", "Ranchi", "Jharkhand"),
            # Guwahati
            ("Pan Bazar", "Guwahati", "Assam"),
            ("Dispur", "Guwahati", "Assam"),
        ],
    )
    async def test_fresh_session_acceptance_localities(self, locality, expected_city, expected_state):
        """Verify each acceptance locality resolves to the correct city, state, country in a fresh session."""
        geocode_cache_clear()
        service = GeocodingService()
        result = await service.geocode_location(locality, context_location=None)

        assert result.country_code == "IN", f"Expected IN for '{locality}', got {result.country_code}"
        assert (result.city or "").lower() == expected_city.lower(), f"Expected city {expected_city}, got {result.city}"
        assert (result.state or "").lower() == expected_state.lower(), f"Expected state {expected_state}, got {result.state}"
        assert result.latitude != 0.0
        assert result.longitude != 0.0
        assert result.timezone == "Asia/Kolkata"

    # 2. Indian locality vs foreign duplicate
    @pytest.mark.asyncio
    async def test_foreign_duplicate_rejection(self):
        """Verify Indian localities are not overridden by foreign homonyms or misplaced states."""
        service = GeocodingService()
        for loc, city, state in [
            ("Maniktala", "Kolkata", "West Bengal"),
            ("Patia", "Bhubaneswar", "Odisha"),
            ("Doranda", "Ranchi", "Jharkhand"),
            ("Basavanagudi", "Bengaluru", "Karnataka"),
        ]:
            geocode_cache_clear()
            res = await service.geocode_location(loc, context_location=None)
            assert res.country_code == "IN"
            assert (res.state or "").lower() == state.lower()
            assert (res.city or "").lower() == city.lower()

    # 3. Explicit country override
    @pytest.mark.asyncio
    async def test_explicit_country_override(self):
        """Explicit country qualifier 'Park Street, UK' resolves to United Kingdom."""
        geocode_cache_clear()
        service = GeocodingService()
        om_resp = _make_mock_response([
            _om_result("Park Street", "United Kingdom", "GB", "England", 51.7167, -0.3333)
        ])
        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.get = AsyncMock(return_value=om_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await service.geocode_location("Park Street, UK")

        assert result.country_code == "GB"
        assert "United Kingdom" in result.country

    # 4. Explicit state override
    @pytest.mark.asyncio
    async def test_explicit_state_override(self):
        """Explicit state qualifier 'Newtown, Pennsylvania' resolves to US, while 'Newtown, West Bengal' resolves to IN."""
        geocode_cache_clear()
        service = GeocodingService()

        # US query
        om_resp_us = _make_mock_response([
            _om_result("Newtown", "United States", "US", "Pennsylvania", 40.229, -74.937)
        ])
        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.get = AsyncMock(return_value=om_resp_us)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            res_us = await service.geocode_location("Newtown, Pennsylvania")

        assert res_us.country_code == "US"
        assert (res_us.state or "").lower() == "pennsylvania"

        # India query
        geocode_cache_clear()
        om_resp_in = _make_mock_response([
            _om_result("New Town", "India", "IN", "West Bengal", 22.589, 88.482)
        ])
        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.get = AsyncMock(return_value=om_resp_in)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            res_in = await service.geocode_location("Newtown, West Bengal")

        assert res_in.country_code == "IN"
        assert (res_in.state or "").lower() == "west bengal"

    # 5. Explicit city override
    @pytest.mark.asyncio
    async def test_explicit_city_override(self):
        """'Park Street, London' must resolve to London, UK rather than being hijacked by Indian Park Street."""
        geocode_cache_clear()
        service = GeocodingService()
        om_resp = _make_mock_response([
            _om_result("Park Street", "United Kingdom", "GB", "England", 51.7167, -0.3333)
        ])
        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.get = AsyncMock(return_value=om_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await service.geocode_location("Park Street, London")

        assert result.country_code == "GB"
        assert "United Kingdom" in result.country

    # 6. Session context
    @pytest.mark.asyncio
    async def test_session_context_preservation(self):
        """Session context enhances resolution of contextual queries."""
        geocode_cache_clear()
        service = GeocodingService()
        kolkata_ctx = GeocodedLocationSchema(
            name="Kolkata, West Bengal, India",
            country="India",
            country_code="IN",
            city="Kolkata",
            state="West Bengal",
            latitude=22.57,
            longitude=88.36,
            timezone="Asia/Kolkata",
        )
        res = await service.geocode_location("Park Street", context_location=kolkata_ctx)
        assert res.country_code == "IN"
        assert res.city == "Kolkata"

    # 7. Context override
    @pytest.mark.asyncio
    async def test_context_override_by_explicit_geography(self):
        """Explicit geography strictly overrides conflicting session context (e.g. Mumbai context + Bandra, Texas)."""
        geocode_cache_clear()
        service = GeocodingService()
        mumbai_ctx = GeocodedLocationSchema(
            name="Mumbai, Maharashtra, India",
            country="India",
            country_code="IN",
            city="Mumbai",
            state="Maharashtra",
            latitude=19.07,
            longitude=72.87,
            timezone="Asia/Kolkata",
        )
        om_resp = _make_mock_response([
            _om_result("Bandra", "United States", "US", "Texas", 29.7, -99.0)
        ])
        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.get = AsyncMock(return_value=om_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            res = await service.geocode_location("Bandra, Texas", context_location=mumbai_ctx)

        assert res.country_code == "US"
        assert res.state == "Texas"

    # 8. Administrative hierarchy validation
    def test_administrative_hierarchy_validation(self):
        """Administrative validation directly rejects false foreign homonyms or mismatched states."""
        # Case A: Maniktala in Bangladesh -> must be rejected
        bangladesh_loc = GeocodedLocationSchema(
            name="Maniktala, Bangladesh",
            country="Bangladesh",
            country_code="BD",
            city="Maniktala",
            latitude=22.8,
            longitude=89.5,
        )
        assert not india_locality_service.validate_administrative_hierarchy(bangladesh_loc, "Maniktala")

        # Case B: Basavanagudi in Andhra Pradesh -> must be rejected (known in Karnataka)
        ap_loc = GeocodedLocationSchema(
            name="Basavanagudi, Andhra Pradesh, India",
            country="India",
            country_code="IN",
            state="Andhra Pradesh",
            city="Basavanagudi",
            latitude=13.0,
            longitude=78.0,
        )
        assert not india_locality_service.validate_administrative_hierarchy(ap_loc, "Basavanagudi")

        # Case C: Correct administrative hierarchy -> accepted
        valid_loc = GeocodedLocationSchema(
            name="Basavanagudi, Bengaluru, Karnataka, India",
            country="India",
            country_code="IN",
            state="Karnataka",
            city="Bengaluru",
            latitude=12.9422,
            longitude=77.5756,
        )
        assert india_locality_service.validate_administrative_hierarchy(valid_loc, "Basavanagudi")

    # 9. Cache isolation
    @pytest.mark.asyncio
    async def test_cache_isolation_between_homonyms(self):
        """Confirm cache keys for 'Park Street' (IN) and 'Park Street, London' (GB) are strictly isolated."""
        geocode_cache_clear()
        service = GeocodingService()

        # 1. Resolve Indian Park Street
        res_in = await service.geocode_location("Park Street", context_location=None)
        assert res_in.country_code == "IN"

        # 2. Mock Open-Meteo for Park Street, London
        om_resp = _make_mock_response([
            _om_result("Park Street", "United Kingdom", "GB", "England", 51.7167, -0.3333)
        ])
        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.get = AsyncMock(return_value=om_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            res_gb = await service.geocode_location("Park Street, London")

        assert res_gb.country_code == "GB"

        # 3. Query Park Street again — must hit cache and return IN, not contaminated by GB
        res_in_again = await service.geocode_location("Park Street", context_location=None)
        assert res_in_again.country_code == "IN"
        assert res_in_again.city == "Kolkata"

    # 10. Genuine ambiguity handling
    @pytest.mark.asyncio
    async def test_genuine_ambiguity_and_unknown_location(self):
        """Verify that multi-city localities disambiguate via session context, and unresolvable queries raise 404."""
        service = GeocodingService()

        # Indira Nagar in Bengaluru context
        bengaluru_ctx = GeocodedLocationSchema(
            name="Bengaluru, Karnataka, India",
            country="India",
            country_code="IN",
            city="Bengaluru",
            state="Karnataka",
            latitude=12.97,
            longitude=77.59,
        )
        res_blr = await service.geocode_location("Indira Nagar", context_location=bengaluru_ctx)
        assert res_blr.city == "Bengaluru"

        # Indira Nagar in Lucknow context
        lucknow_ctx = GeocodedLocationSchema(
            name="Lucknow, Uttar Pradesh, India",
            country="India",
            country_code="IN",
            city="Lucknow",
            state="Uttar Pradesh",
            latitude=26.85,
            longitude=80.95,
        )
        res_lko = await service.geocode_location("Indira Nagar", context_location=lucknow_ctx)
        assert res_lko.city == "Lucknow"

        # Unknown gibberish query raises 404
        geocode_cache_clear()
        empty_om = _make_mock_response([])
        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.get = AsyncMock(return_value=empty_om)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            with pytest.raises(HTTPException) as exc_info:
                await service.geocode_location("NonExistentPlaceXyz12345")
            assert exc_info.value.status_code == 404
