"""Unit tests for weather service, schemas, validation, error handling, caching, deduplication, and API endpoints."""

import app.core.compat  # noqa: F401 — must be imported before FastAPI/pydantic

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import httpx
import pytest

from app.main import app
from app.services.weather_service import WeatherService, get_condition_text, weather_service

client = TestClient(app)

# Mock Open-Meteo current weather payload
MOCK_OPEN_METEO_CURRENT = {
    "latitude": 22.57,
    "longitude": 88.36,
    "timezone": "Asia/Kolkata",
    "current": {
        "time": "2026-09-05T18:00",
        "temperature_2m": 29.5,
        "apparent_temperature": 33.1,
        "relative_humidity_2m": 82,
        "wind_speed_10m": 12.4,
        "precipitation": 0.5,
        "weather_code": 61,
    },
    "hourly": {
        "time": ["2026-09-05T18:00"],
        "precipitation_probability": [75],
    },
}

# Mock Open-Meteo forecast payload
MOCK_OPEN_METEO_FORECAST = {
    "latitude": 22.57,
    "longitude": 88.36,
    "timezone": "Asia/Kolkata",
    "hourly": {
        "time": ["2026-09-05T18:00", "2026-09-05T19:00"],
        "temperature_2m": [29.5, 28.9],
        "weather_code": [61, 3],
        "precipitation_probability": [75, 40],
        "precipitation": [0.5, 0.0],
        "wind_speed_10m": [12.4, 10.1],
    },
}


@pytest.fixture(autouse=True)
def clean_weather_cache():
    """Ensure global weather service cache is cleared before each test."""
    weather_service.clear_cache()
    yield
    weather_service.clear_cache()


def test_get_condition_text():
    """Verify WMO code mapping to human-readable strings."""
    assert get_condition_text(0) == "Clear sky"
    assert get_condition_text(61) == "Slight rain"
    assert get_condition_text(95) == "Thunderstorm"
    assert get_condition_text(999) == "Unknown weather condition"


@patch("app.services.weather_service.weather_service._fetch")
def test_get_current_weather_endpoint_valid(mock_fetch):
    """Test GET /api/weather/current with valid coordinates."""
    mock_fetch.return_value = MOCK_OPEN_METEO_CURRENT

    response = client.get("/api/weather/current?latitude=22.5726&longitude=88.3639")
    assert response.status_code == 200

    data = response.json()
    assert "location" in data
    assert data["location"]["latitude"] == 22.5726
    assert data["location"]["longitude"] == 88.3639
    assert data["location"]["timezone"] == "Asia/Kolkata"

    assert "current" in data
    assert data["current"]["temperature"] == 29.5
    assert data["current"]["feels_like"] == 33.1
    assert data["current"]["condition"] == "Slight rain"
    assert data["current"]["weather_code"] == 61
    assert data["current"]["humidity"] == 82
    assert data["current"]["wind_speed"] == 12.4
    assert data["current"]["precipitation"] == 0.5
    assert data["current"]["precipitation_probability"] == 75

    assert data["source"] == "open-meteo"
    assert "timestamp" in data


@patch("app.services.weather_service.weather_service._fetch")
def test_get_forecast_endpoint_valid(mock_fetch):
    """Test GET /api/weather/forecast with valid parameters."""
    mock_fetch.return_value = MOCK_OPEN_METEO_FORECAST

    response = client.get("/api/weather/forecast?latitude=22.5726&longitude=88.3639&hours=2")
    assert response.status_code == 200

    data = response.json()
    assert "location" in data
    assert len(data["hourly"]) == 2

    first = data["hourly"][0]
    assert first["temperature"] == 29.5
    assert first["condition"] == "Slight rain"
    assert first["precipitation_probability"] == 75

    second = data["hourly"][1]
    assert second["temperature"] == 28.9
    assert second["condition"] == "Overcast"
    assert second["precipitation_probability"] == 40


def test_invalid_latitude():
    """Test out of bounds latitude raises HTTP 400."""
    response = client.get("/api/weather/current?latitude=100.0&longitude=88.3639")
    assert response.status_code == 400
    assert "Latitude must be between -90.0 and 90.0" in response.json()["detail"]


def test_invalid_longitude():
    """Test out of bounds longitude raises HTTP 400."""
    response = client.get("/api/weather/current?latitude=22.5726&longitude=200.0")
    assert response.status_code == 400
    assert "Longitude must be between -180.0 and 180.0" in response.json()["detail"]


def test_invalid_hours():
    """Test out of bounds forecast hours raises HTTP 400."""
    response = client.get("/api/weather/forecast?latitude=22.5726&longitude=88.3639&hours=0")
    assert response.status_code == 400
    assert "Requested forecast hours must be between 1 and 168" in response.json()["detail"]

    response_high = client.get("/api/weather/forecast?latitude=22.5726&longitude=88.3639&hours=200")
    assert response_high.status_code == 400


@patch("app.services.weather_service.httpx.AsyncClient.get")
@pytest.mark.asyncio
async def test_weather_service_timeout(mock_get):
    """Test weather service handles provider gateway timeout cleanly."""
    mock_get.side_effect = httpx.TimeoutException("Connection timed out")
    service = WeatherService(base_retry_delay=0.01)

    with pytest.raises(Exception) as exc_info:
        await service.get_current_weather(22.5726, 88.3639)

    assert "Weather provider gateway timeout" in str(exc_info.value)


@patch("app.services.weather_service.httpx.AsyncClient.get")
@pytest.mark.asyncio
async def test_weather_service_network_error(mock_get):
    """Test weather service handles provider network error cleanly."""
    mock_get.side_effect = httpx.RequestError("Network down")
    service = WeatherService(base_retry_delay=0.01)

    with pytest.raises(Exception) as exc_info:
        await service.get_current_weather(22.5726, 88.3639)

    assert "Weather provider network request failed" in str(exc_info.value)


@patch("app.services.weather_service.weather_service._fetch")
def test_malformed_provider_response(mock_fetch):
    """Test backend handles unparseable provider data without crashing."""
    mock_fetch.return_value = {"invalid": "payload"}

    response = client.get("/api/weather/current?latitude=22.5726&longitude=88.3639")
    assert response.status_code == 502
    assert "Failed to parse weather provider response" in response.json()["detail"]


# ==============================================================================
# Caching, Deduplication, 429 Retry, and Stale Fallback Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_weather_service_caching_and_hit():
    """Verify that identical coordinates and params hit the in-memory cache without duplicate HTTP requests."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_OPEN_METEO_CURRENT
    mock_client.get.return_value = mock_response

    service = WeatherService(client=mock_client, fresh_ttl=60.0)

    # First fetch -> triggers HTTP GET
    res1 = await service.get_current_weather(22.5726, 88.3639)
    assert res1.current.temperature == 29.5
    assert mock_client.get.call_count == 1

    # Second fetch for identical/close coordinates -> served from cache
    res2 = await service.get_current_weather(22.5726, 88.3639)
    assert res2.current.temperature == 29.5
    assert mock_client.get.call_count == 1  # No additional HTTP request made!


@pytest.mark.asyncio
async def test_weather_service_request_deduplication():
    """Verify concurrent requests for the same location are deduplicated into a single provider call."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    async def delayed_get(*args, **kwargs):
        await asyncio.sleep(0.05)
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.json.return_value = MOCK_OPEN_METEO_CURRENT
        return resp

    mock_client.get.side_effect = delayed_get
    service = WeatherService(client=mock_client)

    # Launch 5 concurrent calls
    tasks = [service.get_current_weather(22.5726, 88.3639) for _ in range(5)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 5
    for r in results:
        assert r.current.temperature == 29.5
    # Must only have called the provider once!
    assert mock_client.get.call_count == 1


@pytest.mark.asyncio
async def test_weather_service_429_retry_and_success():
    """Verify that receiving HTTP 429 from provider triggers exponential backoff and succeeds on retry."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    resp_429 = MagicMock(spec=httpx.Response)
    resp_429.status_code = 429
    resp_429.headers = {"Retry-After": "0.01"}

    resp_200 = MagicMock(spec=httpx.Response)
    resp_200.status_code = 200
    resp_200.json.return_value = MOCK_OPEN_METEO_CURRENT

    # First attempt returns 429, second attempt returns 200 OK
    mock_client.get.side_effect = [resp_429, resp_200]

    service = WeatherService(client=mock_client, base_retry_delay=0.01)
    res = await service.get_current_weather(22.5726, 88.3639)

    assert res.current.temperature == 29.5
    assert mock_client.get.call_count == 2


@pytest.mark.asyncio
async def test_weather_service_stale_cache_fallback_on_429():
    """Verify that when the provider returns 429 and retries are exhausted, stale cache is returned gracefully."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    # Populate cache initially
    resp_200 = MagicMock(spec=httpx.Response)
    resp_200.status_code = 200
    resp_200.json.return_value = MOCK_OPEN_METEO_CURRENT
    mock_client.get.return_value = resp_200

    service = WeatherService(client=mock_client, fresh_ttl=0.01, stale_ttl=3600.0, base_retry_delay=0.01)
    initial_res = await service.get_current_weather(22.5726, 88.3639)
    assert initial_res.current.temperature == 29.5
    assert mock_client.get.call_count == 1

    # Wait for fresh TTL to expire (so it becomes stale)
    await asyncio.sleep(0.02)

    # Configure provider to now continuously return 429
    resp_429 = MagicMock(spec=httpx.Response)
    resp_429.status_code = 429
    resp_429.headers = {}
    resp_429.raise_for_status.side_effect = httpx.HTTPStatusError("429 Too Many Requests", request=None, response=resp_429)
    mock_client.get.side_effect = [resp_429, resp_429, resp_429, resp_429]

    # Should gracefully serve stale cache without raising 502/504
    fallback_res = await service.get_current_weather(22.5726, 88.3639)
    assert fallback_res.current.temperature == 29.5


@pytest.mark.asyncio
async def test_weather_service_429_exhausted_no_cache():
    """Verify that when 429 retries are exhausted and NO cached data exists, an appropriate HTTPException is raised."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    resp_429 = MagicMock(spec=httpx.Response)
    resp_429.status_code = 429
    resp_429.headers = {}
    resp_429.raise_for_status.side_effect = httpx.HTTPStatusError("429 Too Many Requests", request=None, response=resp_429)
    mock_client.get.side_effect = [resp_429, resp_429, resp_429, resp_429]

    service = WeatherService(client=mock_client, max_retries=2, base_retry_delay=0.01)

    with pytest.raises(Exception) as exc_info:
        await service.get_current_weather(28.6139, 77.2090)

    assert "429" in str(exc_info.value) or "Rate limit" in str(exc_info.value)


@pytest.mark.asyncio
async def test_weather_service_different_locations_cached_independently():
    """Verify different coordinate locations maintain independent cache entries."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    delhi_payload = dict(MOCK_OPEN_METEO_CURRENT)
    delhi_payload["latitude"] = 28.61
    delhi_payload["longitude"] = 77.20

    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.return_value = delhi_payload
    mock_client.get.return_value = resp

    service = WeatherService(client=mock_client, fresh_ttl=60.0)

    # Fetch Kolkata
    await service.get_current_weather(22.5726, 88.3639)
    assert mock_client.get.call_count == 1

    # Fetch Delhi -> must trigger new HTTP GET
    await service.get_current_weather(28.6139, 77.2090)
    assert mock_client.get.call_count == 2
