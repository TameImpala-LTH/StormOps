"""Comprehensive unit tests for Global Geocoding and Location Resolution."""

import app.core.compat  # noqa: F401
import pytest
from fastapi import HTTPException
from app.services.geocoding_service import (
    geocoding_service,
    geocode_cache_clear,
    geocode_cache_size,
    geocode_cache_keys,
    _cache_set,
    _GEOCODE_CACHE_MAX,
)
from app.schemas.query import GeocodedLocationSchema


@pytest.mark.asyncio
async def test_global_international_cities_resolve_successfully():
    """Verify international cities resolve to their respective countries and coordinates."""
    # Paris
    paris = await geocoding_service.geocode_location("Paris")
    assert paris is not None
    assert "Paris" in paris.name
    assert paris.country == "France" or paris.country_code == "FR"
    assert 48.0 <= paris.latitude <= 49.5

    # London
    london = await geocoding_service.geocode_location("London")
    assert london is not None
    assert "London" in london.name
    assert london.country == "United Kingdom" or london.country_code == "GB"
    assert 51.0 <= london.latitude <= 52.0

    # Tokyo
    tokyo = await geocoding_service.geocode_location("Tokyo")
    assert tokyo is not None
    assert "Tokyo" in tokyo.name
    assert tokyo.country == "Japan" or tokyo.country_code == "JP"
    assert 35.0 <= tokyo.latitude <= 36.5

    # New York
    ny = await geocoding_service.geocode_location("New York")
    assert ny is not None
    assert "New York" in ny.name
    assert ny.country == "United States" or ny.country_code == "US"
    assert 40.0 <= ny.latitude <= 41.5

    # Sydney
    sydney = await geocoding_service.geocode_location("Sydney")
    assert sydney is not None
    assert "Sydney" in sydney.name
    assert sydney.country == "Australia" or sydney.country_code == "AU"
    assert -34.5 <= sydney.latitude <= -33.0

    # Dubai
    dubai = await geocoding_service.geocode_location("Dubai")
    assert dubai is not None
    assert "Dubai" in dubai.name
    assert "United Arab Emirates" in dubai.country or dubai.country_code == "AE"
    assert 24.5 <= dubai.latitude <= 25.5


@pytest.mark.asyncio
async def test_indian_cities_and_aliases():
    """Verify Indian cities and historical aliases resolve correctly to India."""
    # Kolkata
    kolkata = await geocoding_service.geocode_location("Kolkata")
    assert kolkata.country == "India"
    assert kolkata.country_code == "IN"
    assert "Kolkata" in kolkata.name

    # Calcutta alias -> Kolkata
    calcutta = await geocoding_service.geocode_location("Calcutta")
    assert calcutta.country == "India"
    assert calcutta.country_code == "IN"
    assert "Kolkata" in calcutta.name

    # Bangalore alias -> Bengaluru
    bangalore = await geocoding_service.geocode_location("Bangalore")
    assert bangalore.country == "India"
    assert bangalore.country_code == "IN"
    assert "Bengaluru" in bangalore.name

    # Bengaluru
    bengaluru = await geocoding_service.geocode_location("Bengaluru")
    assert bengaluru.country == "India"
    assert bengaluru.country_code == "IN"
    assert "Bengaluru" in bengaluru.name

    # Bombay alias -> Mumbai
    bombay = await geocoding_service.geocode_location("Bombay")
    assert bombay.country == "India"
    assert bombay.country_code == "IN"
    assert "Mumbai" in bombay.name

    # Madras alias -> Chennai
    madras = await geocoding_service.geocode_location("Madras")
    assert madras.country == "India"
    assert madras.country_code == "IN"
    assert "Chennai" in madras.name

    # Delhi
    delhi = await geocoding_service.geocode_location("Delhi")
    assert delhi.country == "India"
    assert delhi.country_code == "IN"

    # Ooty -> Udhagamandalam
    ooty = await geocoding_service.geocode_location("Ooty")
    assert ooty.country == "India"
    assert ooty.country_code == "IN"
    assert "Udhagamandalam" in ooty.name or "Ooty" in ooty.name

    # Darjeeling
    darj = await geocoding_service.geocode_location("Darjeeling")
    assert darj.country == "India"
    assert darj.country_code == "IN"
    assert "Darjeeling" in darj.name


@pytest.mark.asyncio
async def test_ambiguous_indian_regions_labeled_honestly():
    """Verify ambiguous Indian state/region queries preserve geographic entity and label as region."""
    kerala = await geocoding_service.geocode_location("Kerala")
    assert kerala.country == "India"
    assert kerala.country_code == "IN"
    assert "(Region)" in kerala.name
    assert "Kerala" in kerala.name
    assert "Finland" not in kerala.country

    goa = await geocoding_service.geocode_location("Goa")
    assert goa.country == "India"
    assert goa.country_code == "IN"
    assert "(Region)" in goa.name

    punjab = await geocoding_service.geocode_location("Punjab")
    assert punjab.country == "India"
    assert punjab.country_code == "IN"
    assert "(Region)" in punjab.name


@pytest.mark.asyncio
async def test_explicit_country_qualified_queries():
    """Verify country-qualified queries disambiguate properly."""
    london_uk = await geocoding_service.geocode_location("London, UK")
    assert london_uk.country_code == "GB" or "United Kingdom" in london_uk.country

    paris_fr = await geocoding_service.geocode_location("Paris, France")
    assert paris_fr.country_code == "FR" or "France" in paris_fr.country

    delhi_in = await geocoding_service.geocode_location("Delhi, India")
    assert delhi_in.country_code == "IN" or "India" in delhi_in.country

    springfield_us = await geocoding_service.geocode_location("Springfield, USA")
    assert springfield_us.country_code == "US" or "United States" in springfield_us.country


@pytest.mark.asyncio
async def test_geocoding_cache_hit_and_consistency():
    """Verify that repeated lookups hit the in-memory cache and return identical objects."""
    geocode_cache_clear()
    assert geocode_cache_size() == 0

    # First call - cache miss
    loc1 = await geocoding_service.geocode_location("Mumbai")
    assert geocode_cache_size() >= 1

    # Second call - cache hit
    loc2 = await geocoding_service.geocode_location("Mumbai")
    assert loc1.latitude == loc2.latitude
    assert loc1.longitude == loc2.longitude
    assert loc1.name == loc2.name


@pytest.mark.asyncio
async def test_geocoding_cache_normalization_and_alias_sharing():
    """Verify that case differences, extra spaces, and historical aliases share cache entries."""
    geocode_cache_clear()

    # Seed with canonical name
    loc_bengaluru = await geocoding_service.geocode_location("Bengaluru")
    initial_size = geocode_cache_size()
    assert initial_size >= 1

    # Alias "Bangalore" should map to the same key and hit cache without increasing cache size
    loc_bangalore = await geocoding_service.geocode_location("Bangalore")
    assert loc_bangalore.latitude == loc_bengaluru.latitude
    assert loc_bangalore.longitude == loc_bengaluru.longitude
    assert geocode_cache_size() == initial_size

    # Case insensitive & whitespace variations
    loc_variant = await geocoding_service.geocode_location("  bEnGaLuRu  ")
    assert loc_variant.latitude == loc_bengaluru.latitude
    assert geocode_cache_size() == initial_size


@pytest.mark.asyncio
async def test_geocoding_cache_does_not_cache_failures():
    """Verify that unresolvable locations raise 404 and are NEVER cached."""
    geocode_cache_clear()
    before_size = geocode_cache_size()

    with pytest.raises(HTTPException) as exc_info:
        await geocoding_service.geocode_location("NonExistentFakeCityName98765xyz")
    assert exc_info.value.status_code == 404
    assert geocode_cache_size() == before_size


@pytest.mark.asyncio
async def test_geocoding_cache_bounded_lru_eviction():
    """Verify that the cache respects maximum capacity and evicts oldest items in LRU order."""
    geocode_cache_clear()

    # Insert items up to limit
    dummy_item = GeocodedLocationSchema(
        name="Test",
        country="TestCountry",
        latitude=12.34,
        longitude=56.78,
        timezone="UTC",
    )

    for i in range(_GEOCODE_CACHE_MAX + 10):
        await _cache_set(f"test_key_{i}", dummy_item)

    # Size must not exceed max
    assert geocode_cache_size() == _GEOCODE_CACHE_MAX

    # Oldest 10 items (0..9) must have been evicted
    keys = geocode_cache_keys()
    assert "test_key_0" not in keys
    assert "test_key_9" not in keys
    assert f"test_key_{_GEOCODE_CACHE_MAX + 9}" in keys

    # Clean up
    geocode_cache_clear()
