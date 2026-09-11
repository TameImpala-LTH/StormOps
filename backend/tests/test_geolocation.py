"""Comprehensive regression tests for Phase 9 device location resolution, text-override priority, and reverse geocoding."""

import app.core.compat  # noqa: F401
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.schemas.query import GeocodedLocationSchema
from app.schemas.weather import (
    CurrentWeather,
    CurrentWeatherResponse,
    ForecastResponse,
    HourlyForecast,
    LocationCoordinates,
)
from app.services.geocoding_service import geocoding_service
from app.services.query_service import SESSION_CONTEXT

client = TestClient(app)

MOCK_KOLKATA = GeocodedLocationSchema(
    name="Kolkata",
    country="India",
    admin1="West Bengal",
    latitude=22.5726,
    longitude=88.3639,
    timezone="Asia/Kolkata",
)

MOCK_PARIS = GeocodedLocationSchema(
    name="Paris",
    country="France",
    admin1="Ile-de-France",
    latitude=48.8534,
    longitude=2.3488,
    timezone="Europe/Paris",
)

MOCK_CURRENT_KOLKATA = CurrentWeatherResponse(
    location=LocationCoordinates(
        latitude=22.5726, longitude=88.3639, name="Kolkata", timezone="Asia/Kolkata"
    ),
    current=CurrentWeather(
        temperature=30.0,
        feels_like=33.0,
        condition="Partly cloudy",
        weather_code=2,
        humidity=75,
        wind_speed=12.0,
        precipitation=0.0,
        precipitation_probability=20,
        time="2026-09-06T12:00",
    ),
    source="open-meteo",
    timestamp="2026-09-06T12:00:00Z",
)

MOCK_FORECAST_KOLKATA = ForecastResponse(
    location=LocationCoordinates(
        latitude=22.5726, longitude=88.3639, name="Kolkata", timezone="Asia/Kolkata"
    ),
    hourly=[
        HourlyForecast(
            time="2026-09-06T12:00",
            temperature=30.0,
            condition="Partly cloudy",
            weather_code=2,
            precipitation_probability=20,
            precipitation=0.0,
            wind_speed=12.0,
        )
    ],
    source="open-meteo",
    timestamp="2026-09-06T12:00:00Z",
)


@pytest.mark.asyncio
async def test_reverse_geocode_direct():
    """Test reverse geocoding direct service method returns resolved model."""
    res = await geocoding_service.reverse_geocode(22.5726, 88.3639)
    assert res is not None
    assert isinstance(res, GeocodedLocationSchema)
    assert res.latitude == 22.5726
    assert res.longitude == 88.3639


@patch("app.services.query_service.geocoding_service.geocode_location")
@patch("app.services.query_service.geocoding_service.reverse_geocode")
@patch("app.services.weather_service.weather_service.get_current_weather")
@patch("app.services.weather_service.weather_service.get_forecast")
def test_regression_a_structured_coords_plus_my_location_text(
    mock_forecast, mock_current, mock_reverse_geo, mock_geocode_location
):
    """Test A: Structured coordinates + 'my location' text uses coordinates and does NOT attempt to resolve 'My Location'."""
    test_session = "test_session_regression_a"
    SESSION_CONTEXT.pop(test_session, None)

    mock_reverse_geo.return_value = MOCK_KOLKATA
    mock_current.return_value = MOCK_CURRENT_KOLKATA
    mock_forecast.return_value = MOCK_FORECAST_KOLKATA

    payload = {
        "message": "What's the weather at my location?",
        "session_id": test_session,
        "location": {
            "latitude": 22.5726,
            "longitude": 88.3639
        }
    }

    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["needs_clarification"] is False
    assert data["location"]["latitude"] == 22.5726
    assert data["location"]["longitude"] == 88.3639

    # CRITICAL: geocode_location must NOT be called for "My Location"!
    mock_geocode_location.assert_not_called()


@patch("app.services.query_service.geocoding_service.reverse_geocode")
@patch("app.services.weather_service.weather_service.get_current_weather")
@patch("app.services.weather_service.weather_service.get_forecast")
def test_regression_b_structured_coords_reverse_geocode_resolved_name(
    mock_forecast, mock_current, mock_reverse_geo
):
    """Test B: Structured coordinates reverse-geocode successfully returning city, country, state."""
    test_session = "test_session_regression_b"
    SESSION_CONTEXT.pop(test_session, None)

    mock_reverse_geo.return_value = MOCK_KOLKATA
    mock_current.return_value = MOCK_CURRENT_KOLKATA
    mock_forecast.return_value = MOCK_FORECAST_KOLKATA

    payload = {
        "message": "What's the weather at my location?",
        "session_id": test_session,
        "location": {
            "latitude": 22.5726,
            "longitude": 88.3639
        }
    }

    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["location"]["name"] == "Kolkata"
    assert data["location"]["country"] == "India"


@patch("app.services.query_service.geocoding_service.reverse_geocode")
@patch("app.services.weather_service.weather_service.get_current_weather")
@patch("app.services.weather_service.weather_service.get_forecast")
def test_regression_c_structured_coords_remain_weather_source(
    mock_forecast, mock_current, mock_reverse_geo
):
    """Test C: Structured coordinates remain the weather source (exact lat/lon passed to Open-Meteo)."""
    test_session = "test_session_regression_c"
    SESSION_CONTEXT.pop(test_session, None)

    mock_reverse_geo.return_value = MOCK_KOLKATA
    mock_current.return_value = MOCK_CURRENT_KOLKATA
    mock_forecast.return_value = MOCK_FORECAST_KOLKATA

    payload = {
        "message": "What's the weather at my location?",
        "session_id": test_session,
        "location": {
            "latitude": 22.5726,
            "longitude": 88.3639
        }
    }

    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200

    mock_current.assert_called_once_with(22.5726, 88.3639)
    mock_forecast.assert_called_once_with(22.5726, 88.3639, hours=168)


@patch("app.services.query_service.geocoding_service.geocode_location")
@patch("app.services.weather_service.weather_service.get_current_weather")
@patch("app.services.weather_service.weather_service.get_forecast")
def test_regression_d_existing_textual_location_query(
    mock_forecast, mock_current, mock_geocode
):
    """Test D: Existing textual location query still works exactly as before."""
    test_session = "test_session_regression_d"
    SESSION_CONTEXT.pop(test_session, None)

    mock_geocode.return_value = MOCK_PARIS
    mock_current.return_value = MOCK_CURRENT_KOLKATA
    mock_forecast.return_value = MOCK_FORECAST_KOLKATA

    response = client.post(
        "/api/chat",
        json={"message": "What's the weather in Paris?", "session_id": test_session}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["location"]["name"] == "Paris"
    mock_geocode.assert_called_once_with("Paris")


@patch("app.services.query_service.geocoding_service.reverse_geocode")
@patch("app.services.weather_service.weather_service.get_current_weather")
@patch("app.services.weather_service.weather_service.get_forecast")
def test_regression_e_structured_coords_win_over_existing_session_location(
    mock_forecast, mock_current, mock_reverse_geo
):
    """Test E: Structured coordinates win when session already contains a different location."""
    test_session = "test_session_regression_e"
    # Seed session with Paris
    SESSION_CONTEXT[test_session] = {"location": MOCK_PARIS}

    mock_reverse_geo.return_value = MOCK_KOLKATA
    mock_current.return_value = MOCK_CURRENT_KOLKATA
    mock_forecast.return_value = MOCK_FORECAST_KOLKATA

    payload = {
        "message": "What's the weather at my location?",
        "session_id": test_session,
        "location": {
            "latitude": 22.5726,
            "longitude": 88.3639
        }
    }

    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Structured coordinates (Kolkata) MUST win over existing session location (Paris)!
    assert data["location"]["name"] == "Kolkata"
    assert data["location"]["latitude"] == 22.5726


@patch("app.services.geocoding_service.httpx.AsyncClient.get")
@pytest.mark.asyncio
async def test_regression_f_locality_hierarchy_reverse_geocoding(mock_get):
    """Test F: Reverse geocode returns '{locality}, {city}' hierarchy when suburb/neighbourhood is present."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "address": {
            "suburb": "Behala",
            "city": "Kolkata",
            "state": "West Bengal",
            "country": "India",
        }
    }
    mock_get.return_value = mock_response

    res = await geocoding_service.reverse_geocode(22.4988, 88.3103)
    assert res.name == "Behala, Kolkata"
    assert res.latitude == 22.4988
    assert res.longitude == 88.3103
    assert res.country == "India"
    assert res.admin1 == "West Bengal"

