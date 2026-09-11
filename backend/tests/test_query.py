"""Unit tests for geocoding service, query entity extraction, grounded summary, and POST /api/weather/query endpoint."""

import app.core.compat  # noqa: F401 — must be imported before FastAPI/pydantic

from unittest.mock import AsyncMock, patch
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
from app.services.query_service import extract_query_entities, generate_grounded_summary

client = TestClient(app)

# Mock Geocoded Location data
MOCK_GEOCODED = GeocodedLocationSchema(
    name="Darjeeling",
    country="India",
    admin1="West Bengal",
    latitude=27.03333,
    longitude=88.26667,
    timezone="Asia/Kolkata",
)

MOCK_CURRENT_RESPONSE = CurrentWeatherResponse(
    location=LocationCoordinates(
        latitude=27.03333, longitude=88.26667, name="Darjeeling", timezone="Asia/Kolkata"
    ),
    current=CurrentWeather(
        temperature=18.5,
        feels_like=18.5,
        condition="Partly cloudy",
        weather_code=2,
        humidity=70,
        wind_speed=8.0,
        precipitation=0.0,
        precipitation_probability=10,
        time="2026-09-06T00:00",
    ),
    source="open-meteo",
    timestamp="2026-09-06T00:00:00Z",
)

MOCK_FORECAST_RESPONSE = ForecastResponse(
    location=LocationCoordinates(
        latitude=27.03333, longitude=88.26667, name="Darjeeling", timezone="Asia/Kolkata"
    ),
    hourly=[
        HourlyForecast(
            time="2026-09-06T00:00",
            temperature=18.5,
            condition="Partly cloudy",
            weather_code=2,
            precipitation_probability=10,
            precipitation=0.0,
            wind_speed=8.0,
        )
    ],
    source="open-meteo",
    timestamp="2026-09-06T00:00:00Z",
)


def test_extract_query_entities():
    """Verify entity extraction for various natural language weather queries."""
    res1 = extract_query_entities("Will it rain in Kolkata tomorrow evening?")
    assert res1.intent == "rain_query"
    assert res1.extracted_location == "Kolkata"
    assert res1.date_context == "tomorrow"
    assert res1.time_period == "evening"

    res2 = extract_query_entities("Should I carry an umbrella in Darjeeling tomorrow?")
    assert res2.intent == "umbrella_recommendation"
    assert res2.extracted_location == "Darjeeling"
    assert res2.date_context == "tomorrow"

    res3 = extract_query_entities("How hot will Delhi be tonight?")
    assert res3.intent == "temperature_query"
    assert res3.extracted_location == "Delhi"
    assert res3.time_period == "tonight"

    res4 = extract_query_entities("What's the weather in Paris?")
    assert res4.intent == "weather_information"
    assert res4.extracted_location == "Paris"

    res5 = extract_query_entities("Is it a good time to go for a walk in Kolkata?")
    assert res5.intent == "outdoor_activity_recommendation"
    assert res5.extracted_location == "Kolkata"


def test_generate_grounded_summary():
    """Verify natural language summary generation is grounded strictly in input metrics."""
    entities = extract_query_entities("Will it rain in Kolkata tomorrow evening?")
    summary = generate_grounded_summary(
        query_info=entities,
        location_name="Kolkata, India",
        temp=28.5,
        feels_like=33.0,
        condition="Moderate rain",
        humidity=85,
        wind_speed=10.0,
        precip_prob=75,
        precip=1.5,
    )
    assert "Rain is possible in Kolkata, India" in summary
    assert "75%" in summary
    assert "umbrella" in summary



@patch("app.services.query_service.geocoding_service.geocode_location")
@patch("app.services.weather_service.weather_service.get_current_weather")
@patch("app.services.weather_service.weather_service.get_forecast")
def test_post_query_endpoint_success(mock_forecast, mock_current, mock_geocode):
    """Test POST /api/weather/query with valid natural language request."""
    mock_geocode.return_value = MOCK_GEOCODED
    mock_current.return_value = MOCK_CURRENT_RESPONSE
    mock_forecast.return_value = MOCK_FORECAST_RESPONSE

    payload = {"message": "Should I carry an umbrella in Darjeeling tomorrow?"}
    response = client.post("/api/weather/query", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert "query" in data
    assert data["query"]["intent"] == "umbrella_recommendation"
    assert data["query"]["extracted_location"] == "Darjeeling"

    assert "location" in data
    assert data["location"]["name"] == "Darjeeling"
    assert data["location"]["country"] == "India"
    assert data["location"]["latitude"] == 27.03333

    assert "current" in data
    assert data["current"]["temperature"] == 18.5

    assert "summary" in data
    assert "Darjeeling" in data["summary"]


def test_post_query_endpoint_invalid_payload():
    """Test POST /api/weather/query with invalid/empty payload."""
    response = client.post("/api/weather/query", json={"message": "a"})
    assert response.status_code == 422
