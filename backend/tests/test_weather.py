"""Unit tests for weather service, schemas, validation, error handling, caching, deduplication, and API endpoints."""

import app.core.compat  # noqa: F401 — must be imported before FastAPI/pydantic

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
import httpx
import pytest

from app.main import app
from app.services.weather_service import WeatherService, get_condition_text, weather_service

client = TestClient(app)

# Mock Open-Meteo unified weather payload (containing both current and hourly)
MOCK_OPEN_METEO_UNIFIED = {
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
        "time": ["2026-09-05T18:00", "2026-09-05T19:00"],
        "temperature_2m": [29.5, 28.9],
        "apparent_temperature": [33.1, 32.0],
        "relative_humidity_2m": [82, 85],
        "weather_code": [61, 3],
        "precipitation_probability": [75, 40],
        "precipitation": [0.5, 0.0],
        "wind_speed_10m": [12.4, 10.1],
    },
}

MOCK_OPEN_METEO_CURRENT = MOCK_OPEN_METEO_UNIFIED
MOCK_OPEN_METEO_FORECAST = MOCK_OPEN_METEO_UNIFIED


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
# Unified Bundle, Caching, Deduplication, 429 Retry, and Stale Fallback Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_weather_bundle_single_request():
    """Verify that get_weather_bundle returns both current and forecast with EXACTLY ONE HTTP request."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_OPEN_METEO_UNIFIED
    mock_client.get.return_value = mock_response

    service = WeatherService(client=mock_client)
    curr, forecast = await service.get_weather_bundle(22.5726, 88.3639, hours=24)

    assert curr.current.temperature == 29.5
    assert len(forecast.hourly) == 2
    assert forecast.hourly[0].temperature == 29.5
    assert mock_client.get.call_count == 1  # Exactly ONE HTTP request made!


@pytest.mark.asyncio
async def test_cache_shared_between_current_and_forecast():
    """Verify that calling get_current_weather and then get_forecast for the same location reuses the same cache."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_OPEN_METEO_UNIFIED
    mock_client.get.return_value = mock_response

    service = WeatherService(client=mock_client, fresh_ttl=60.0)

    # 1. Device location check calls get_current_weather
    curr = await service.get_current_weather(22.5726, 88.3639)
    assert curr.current.temperature == 29.5
    assert mock_client.get.call_count == 1

    # 2. Subsequent chat query calls get_forecast or get_weather_bundle for the same coordinates
    forecast = await service.get_forecast(22.5726, 88.3639, hours=24)
    assert forecast.hourly[0].temperature == 29.5
    assert mock_client.get.call_count == 1  # Zero additional HTTP requests!

    bundle_curr, bundle_forecast = await service.get_weather_bundle(22.5726, 88.3639, hours=24)
    assert bundle_curr.current.temperature == 29.5
    assert mock_client.get.call_count == 1  # Still zero additional HTTP requests!


@pytest.mark.asyncio
async def test_weather_service_caching_and_hit():
    """Verify that identical coordinates and params hit the in-memory cache without duplicate HTTP requests."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_OPEN_METEO_UNIFIED
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
        resp.json.return_value = MOCK_OPEN_METEO_UNIFIED
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
    resp_200.json.return_value = MOCK_OPEN_METEO_UNIFIED

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
    resp_200.json.return_value = MOCK_OPEN_METEO_UNIFIED
    mock_client.get.return_value = resp_200

    service = WeatherService(
        client=mock_client,
        fresh_ttl=0.01,
        stale_ttl=3600.0,
        base_retry_delay=0.01,
        openweather_service=MagicMock(is_configured=False),
    )
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

    service = WeatherService(
        client=mock_client,
        max_retries=2,
        base_retry_delay=0.01,
        openweather_service=MagicMock(is_configured=False),
    )

    with pytest.raises(Exception) as exc_info:
        await service.get_current_weather(28.6139, 77.2090)

    assert "429" in str(exc_info.value) or "Rate limit" in str(exc_info.value)


@pytest.mark.asyncio
async def test_weather_service_different_locations_cached_independently():
    """Verify different coordinate locations maintain independent cache entries."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    delhi_payload = dict(MOCK_OPEN_METEO_UNIFIED)
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


@pytest.mark.asyncio
async def test_weather_service_429_diagnostic_logging_and_no_secrets(caplog):
    """Verify that HTTP 429 triggers diagnostic logging of status and rate limit headers, without leaking secrets."""
    import logging
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    resp_429 = MagicMock(spec=httpx.Response)
    resp_429.status_code = 429
    resp_429.headers = {
        "Retry-After": "2",
        "x-ratelimit-limit-hourly": "10000",
        "x-ratelimit-remaining-hourly": "0",
        "Authorization": "Bearer super-secret-token",
        "apikey": "secret-api-key-12345",
    }
    resp_429.raise_for_status.side_effect = httpx.HTTPStatusError("429 Too Many Requests", request=None, response=resp_429)
    mock_client.get.return_value = resp_429

    service = WeatherService(
        client=mock_client,
        max_retries=0,
        openweather_service=MagicMock(is_configured=False),
    )

    with caplog.at_level(logging.WARNING):
        with pytest.raises(Exception):
            await service.get_current_weather(22.5726, 88.3639)

    # Check that diagnostic logging occurred
    assert any("Open-Meteo HTTP 429" in record.message or "rate limited (HTTP 429)" in record.message for record in caplog.records)

    # Verify rate limit headers were captured
    log_text = " ".join(record.message for record in caplog.records)
    assert "x-ratelimit-limit-hourly" in log_text or "Retry-After" in log_text

    # CRITICAL: Verify secrets are NEVER leaked in logs
    assert "super-secret-token" not in log_text
    assert "secret-api-key-12345" not in log_text


def test_diagnostics_open_meteo_endpoint():
    """Verify that GET /api/diagnostics/open-meteo executes direct check and returns status, headers, body, elapsed_seconds."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"latitude": 22.56263, "current": {"temperature_2m": 28.5}}'
        mock_get.return_value = mock_response

        response = client.get("/api/diagnostics/open-meteo")
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert "headers" in data
        assert "body" in data
        assert "elapsed_seconds" in data
        assert "temperature_2m" in data["body"]


# ==============================================================================
# OpenWeather Secondary Fallback Provider Tests
# ==============================================================================

MOCK_OWM_CURRENT = {
    "coord": {"lon": 88.3639, "lat": 22.5726},
    "weather": [{"id": 801, "main": "Clouds", "description": "few clouds", "icon": "02d"}],
    "main": {
        "temp": 31.5,
        "feels_like": 35.0,
        "temp_min": 31.0,
        "temp_max": 32.0,
        "humidity": 65,
    },
    "wind": {"speed": 4.0, "deg": 170},  # 4.0 m/s = 14.4 km/h
    "rain": {"1h": 0.8},
    "dt": 1726117200,
    "timezone": 19800,
    "name": "Kolkata",
    "cod": 200,
}

MOCK_OWM_FORECAST = {
    "cod": "200",
    "message": 0,
    "cnt": 2,
    "list": [
        {
            "dt": 1726117200,
            "main": {
                "temp": 31.5,
                "feels_like": 35.0,
                "humidity": 65,
            },
            "weather": [{"id": 500, "main": "Rain", "description": "light rain", "icon": "10d"}],
            "wind": {"speed": 3.0, "deg": 170},  # 3.0 m/s = 10.8 km/h
            "pop": 0.60,
            "rain": {"3h": 1.5},
            "dt_txt": "2026-09-12 06:00:00",
        },
        {
            "dt": 1726128000,
            "main": {
                "temp": 29.0,
                "feels_like": 32.0,
                "humidity": 70,
            },
            "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
            "wind": {"speed": 2.5, "deg": 180},
            "pop": 0.10,
            "dt_txt": "2026-09-12 09:00:00",
        },
    ],
    "city": {
        "id": 1275004,
        "name": "Kolkata",
        "coord": {"lat": 22.5726, "lon": 88.3639},
        "country": "IN",
        "timezone": 19800,
    },
}


@pytest.mark.asyncio
async def test_open_meteo_success_openweather_not_called():
    """1. When Open-Meteo succeeds, OpenWeather fallback is NOT called."""
    mock_om_client = AsyncMock(spec=httpx.AsyncClient)
    resp_200 = MagicMock(spec=httpx.Response)
    resp_200.status_code = 200
    resp_200.json.return_value = MOCK_OPEN_METEO_UNIFIED
    mock_om_client.get.return_value = resp_200

    from app.services.openweather_service import OpenWeatherService
    mock_owm = MagicMock(spec=OpenWeatherService)
    mock_owm.is_configured = True
    mock_owm.fetch_unified_data = AsyncMock()

    service = WeatherService(client=mock_om_client, openweather_service=mock_owm)
    res = await service.get_current_weather(22.5726, 88.3639)

    assert res.current.temperature == 29.5
    assert res.source == "open-meteo"
    assert mock_owm.fetch_unified_data.called is False


@pytest.mark.asyncio
async def test_open_meteo_429_openweather_fallback_called(caplog):
    """2. When Open-Meteo returns HTTP 429, OpenWeather fallback is called and logged."""
    import logging

    mock_om_client = AsyncMock(spec=httpx.AsyncClient)
    resp_429 = MagicMock(spec=httpx.Response)
    resp_429.status_code = 429
    resp_429.headers = {"Retry-After": "1"}
    resp_429.raise_for_status.side_effect = httpx.HTTPStatusError("429 Rate limited", request=None, response=resp_429)
    mock_om_client.get.return_value = resp_429

    from app.services.openweather_service import OpenWeatherService
    mock_owm = MagicMock(spec=OpenWeatherService)
    mock_owm.is_configured = True

    owm_unified = {
        "latitude": 22.5726,
        "longitude": 88.3639,
        "timezone": "UTC+05:30",
        "source": "openweather",
        "current": {
            "time": "2026-09-12T06:00",
            "temperature_2m": 31.5,
            "apparent_temperature": 35.0,
            "relative_humidity_2m": 65,
            "weather_code": 1,
            "wind_speed_10m": 14.4,
            "precipitation": 0.8,
        },
        "hourly": {
            "time": ["2026-09-12T06:00", "2026-09-12T09:00"],
            "temperature_2m": [31.5, 29.0],
            "apparent_temperature": [35.0, 32.0],
            "weather_code": [61, 0],
            "precipitation_probability": [60, 10],
            "precipitation": [1.5, 0.0],
            "wind_speed_10m": [10.8, 9.0],
        },
    }
    mock_owm.fetch_unified_data = AsyncMock(return_value=owm_unified)

    service = WeatherService(client=mock_om_client, max_retries=0, openweather_service=mock_owm)

    with caplog.at_level(logging.INFO):
        res = await service.get_current_weather(22.5726, 88.3639)

    assert res.current.temperature == 31.5
    assert res.source == "openweather"
    assert mock_owm.fetch_unified_data.called is True

    # Verify required diagnostic log strings
    log_text = " ".join(record.message for record in caplog.records)
    assert "Open-Meteo failed" in log_text
    assert "attempting OpenWeather fallback" in log_text
    assert "OpenWeather fallback succeeded" in log_text


@pytest.mark.asyncio
async def test_open_meteo_timeout_openweather_fallback_called(caplog):
    """3. When Open-Meteo times out, OpenWeather fallback is called."""
    import logging

    mock_om_client = AsyncMock(spec=httpx.AsyncClient)
    mock_om_client.get.side_effect = httpx.TimeoutException("Connection timed out")

    from app.services.openweather_service import OpenWeatherService
    mock_owm = MagicMock(spec=OpenWeatherService)
    mock_owm.is_configured = True
    owm_unified = {
        "latitude": 22.5726,
        "longitude": 88.3639,
        "timezone": "UTC+05:30",
        "source": "openweather",
        "current": {
            "time": "2026-09-12T06:00",
            "temperature_2m": 31.5,
            "apparent_temperature": 35.0,
            "relative_humidity_2m": 65,
            "weather_code": 1,
            "wind_speed_10m": 14.4,
            "precipitation": 0.8,
        },
        "hourly": {
            "time": ["2026-09-12T06:00"],
            "temperature_2m": [31.5],
            "apparent_temperature": [35.0],
            "weather_code": [61],
            "precipitation_probability": [60],
            "precipitation": [1.5],
            "wind_speed_10m": [10.8],
        },
    }
    mock_owm.fetch_unified_data = AsyncMock(return_value=owm_unified)

    service = WeatherService(client=mock_om_client, max_retries=0, openweather_service=mock_owm)

    with caplog.at_level(logging.INFO):
        curr, forecast = await service.get_weather_bundle(22.5726, 88.3639, hours=24)

    assert curr.current.temperature == 31.5
    assert curr.source == "openweather"
    assert forecast.hourly[0].temperature == 31.5
    assert mock_owm.fetch_unified_data.called is True


@pytest.mark.asyncio
async def test_openweather_success_normalized_into_existing_schema():
    """4. OpenWeather success is normalized into the exact existing schema contracts."""
    from app.services.openweather_service import OpenWeatherService

    mock_http = AsyncMock(spec=httpx.AsyncClient)
    resp_curr = MagicMock(spec=httpx.Response)
    resp_curr.status_code = 200
    resp_curr.json.return_value = MOCK_OWM_CURRENT

    resp_forecast = MagicMock(spec=httpx.Response)
    resp_forecast.status_code = 200
    resp_forecast.json.return_value = MOCK_OWM_FORECAST

    mock_http.get.side_effect = [resp_curr, resp_forecast]

    owm_service = OpenWeatherService(api_key="test_owm_key", client=mock_http)
    curr_res, forecast_res = await owm_service.get_weather_bundle(22.5726, 88.3639, hours=48)

    # Verify CurrentWeatherResponse contract
    assert curr_res.source == "openweather"
    assert curr_res.current.temperature == 31.5
    assert curr_res.current.feels_like == 35.0
    assert curr_res.current.humidity == 65
    assert curr_res.current.wind_speed == 14.4  # 4.0 m/s * 3.6 = 14.4 km/h
    assert curr_res.current.precipitation == 0.8
    assert curr_res.location.name == "Kolkata"

    # Verify ForecastResponse contract
    assert forecast_res.source == "openweather"
    assert len(forecast_res.hourly) == 2
    assert forecast_res.hourly[0].temperature == 31.5
    assert forecast_res.hourly[0].wind_speed == 10.8  # 3.0 m/s * 3.6 = 10.8 km/h
    assert forecast_res.hourly[0].precipitation_probability == 60  # pop 0.60 -> 60%
    assert forecast_res.hourly[0].weather_code == 61  # OWM id 500 -> WMO 61
    assert forecast_res.hourly[0].condition == "Slight rain"


@pytest.mark.asyncio
async def test_both_providers_fail_graceful_behavior():
    """5. When both Open-Meteo and OpenWeather fail, existing graceful failure behavior (502) is preserved."""
    mock_om_client = AsyncMock(spec=httpx.AsyncClient)
    resp_429 = MagicMock(spec=httpx.Response)
    resp_429.status_code = 429
    resp_429.headers = {}
    resp_429.raise_for_status.side_effect = httpx.HTTPStatusError("429 Rate limit", request=None, response=resp_429)
    mock_om_client.get.return_value = resp_429

    from app.services.openweather_service import OpenWeatherService
    mock_owm = MagicMock(spec=OpenWeatherService)
    mock_owm.is_configured = True
    mock_owm.fetch_unified_data = AsyncMock(side_effect=HTTPException(status_code=502, detail="OpenWeather failed"))

    service = WeatherService(client=mock_om_client, max_retries=0, openweather_service=mock_owm)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_current_weather(22.5726, 88.3639)

    assert exc_info.value.status_code in (502, 504)


def test_missing_openweather_api_key_safe_startup():
    """6. Missing OPENWEATHER_API_KEY does not crash application startup and is_configured is False."""
    from app.services.openweather_service import OpenWeatherService

    service = OpenWeatherService(api_key="")
    assert service.is_configured is False

    service_whitespace = OpenWeatherService(api_key="   ")
    assert service_whitespace.is_configured is False


@pytest.mark.asyncio
async def test_openweather_auth_error_no_retry_no_secret_leak(caplog):
    """7. OpenWeather 401/403 is treated as configuration error, not retried, and never logs secret API key."""
    import logging
    from app.services.openweather_service import OpenWeatherService

    secret_key = "super_secret_openweather_key_12345"
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    resp_401 = MagicMock(spec=httpx.Response)
    resp_401.status_code = 401
    mock_http.get.return_value = resp_401

    service = OpenWeatherService(api_key=secret_key, client=mock_http)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(HTTPException) as exc_info:
            await service.get_current_weather(22.5726, 88.3639)

    assert exc_info.value.status_code == 502
    assert mock_http.get.call_count == 1  # No repeated retry loop

    # Check logs
    log_text = " ".join(record.message for record in caplog.records)
    assert "OpenWeather authentication failed" in log_text
    assert secret_key not in log_text  # Key never leaked in logs!

