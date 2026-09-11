"""Comprehensive unit tests for location comparison and WeatherGPT decision comparison engine."""

import app.core.compat  # noqa: F401
from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.schemas.query import TargetPeriodWeather, GeocodedLocationSchema
from app.schemas.weather import CurrentWeatherResponse, LocationCoordinates, CurrentWeather, ForecastResponse, HourlyForecast
from app.services.comparison_service import comparison_engine_service
from app.services.query_service import extract_query_entities_rule_based, SESSION_CONTEXT
from app.services.llm_service import LLMService

client = TestClient(app)


def test_comparison_intent_extraction_regex():
    """Verify rule-based comparison intent classification and dual location extraction for exact requirement queries."""
    q1 = extract_query_entities_rule_based("Compare Kolkata and Mumbai tomorrow.")
    assert q1.intent == "comparison"
    assert q1.extracted_location_a == "Kolkata"
    assert q1.extracted_location_b == "Mumbai"
    assert q1.date_context == "tomorrow"

    q2 = extract_query_entities_rule_based("Should I travel to Darjeeling or Kolkata this weekend?")
    assert q2.intent == "comparison"
    assert q2.extracted_location_a == "Darjeeling"
    assert q2.extracted_location_b == "Kolkata"
    assert q2.comparison_goal == "travel"

    q3 = extract_query_entities_rule_based("Which is better for outdoor activities tomorrow, Delhi or Mumbai?")
    assert q3.intent == "comparison"
    assert q3.extracted_location_a == "Delhi"
    assert q3.extracted_location_b == "Mumbai"
    assert q3.comparison_goal == "outdoor_activity"

    q4 = extract_query_entities_rule_based("Which place has less rain, Delhi or Mumbai?")
    assert q4.intent == "comparison"
    assert q4.extracted_location_a == "Delhi"
    assert q4.extracted_location_b == "Mumbai"
    assert q4.comparison_goal == "rain"

    q5 = extract_query_entities_rule_based("Where should I go, Kolkata or Mumbai?")
    assert q5.intent == "comparison"
    assert q5.extracted_location_a == "Kolkata"
    assert q5.extracted_location_b == "Mumbai"
    assert q5.comparison_goal == "travel"

    q6 = extract_query_entities_rule_based("Compare Delhi vs Mumbai tomorrow evening.")
    assert q6.intent == "comparison"
    assert q6.extracted_location_a == "Delhi"
    assert q6.extracted_location_b == "Mumbai"
    assert q6.date_context == "tomorrow"
    assert q6.time_period == "evening"

    q7 = extract_query_entities_rule_based("Which is cooler, Delhi or Mumbai?")
    assert q7.intent == "comparison"
    assert q7.extracted_location_a == "Delhi"
    assert q7.extracted_location_b == "Mumbai"
    assert q7.comparison_goal == "cooler"

    q8 = extract_query_entities_rule_based("Which is warmer, Delhi or Mumbai?")
    assert q8.intent == "comparison"
    assert q8.extracted_location_a == "Delhi"
    assert q8.extracted_location_b == "Mumbai"
    assert q8.comparison_goal == "warmer"


def test_temperature_comparison_cooler_semantics():
    """Verify temperature comparison for 'cooler' query recommends lower temperature location with consistent factors."""
    loc_a = GeocodedLocationSchema(name="Delhi", country="India", latitude=28.61, longitude=77.20, timezone="Asia/Kolkata")
    loc_b = GeocodedLocationSchema(name="Mumbai", country="India", latitude=19.07, longitude=72.87, timezone="Asia/Kolkata")

    pw_a = TargetPeriodWeather(
        period_label="tomorrow",
        temperature=30.0,
        feels_like=32.0,
        condition="Clear sky",
        weather_code=0,
        humidity=40,
        wind_speed=10.0,
        precipitation=0.0,
        precipitation_probability=0,
    )
    pw_b = TargetPeriodWeather(
        period_label="tomorrow",
        temperature=27.0,
        feels_like=28.0,
        condition="Partly cloudy",
        weather_code=2,
        humidity=60,
        wind_speed=12.0,
        precipitation=0.0,
        precipitation_probability=10,
    )

    res = comparison_engine_service.compare_locations(
        location_a=loc_a,
        location_b=loc_b,
        pw_a=pw_a,
        pw_b=pw_b,
        alerts_a=[],
        alerts_b=[],
        goal="cooler",
    )

    assert res.decision.recommended_key == "b"
    assert res.decision.recommended_location == "Mumbai"
    assert "Mumbai is cooler" in res.decision.summary
    assert "Mumbai is cooler at 27.0°C compared with Delhi at 30.0°C." in res.decision.winner_reason

    temp_factor = next(f for f in res.decision.factors if f.metric == "temperature")
    assert temp_factor.better_location == "b"
    assert "Mumbai is cooler" in temp_factor.impact_note


def test_temperature_comparison_warmer_semantics():
    """Verify temperature comparison for 'warmer' query recommends higher temperature location with consistent factors."""
    loc_a = GeocodedLocationSchema(name="Delhi", country="India", latitude=28.61, longitude=77.20, timezone="Asia/Kolkata")
    loc_b = GeocodedLocationSchema(name="Mumbai", country="India", latitude=19.07, longitude=72.87, timezone="Asia/Kolkata")

    pw_a = TargetPeriodWeather(
        period_label="tomorrow",
        temperature=30.0,
        feels_like=32.0,
        condition="Clear sky",
        weather_code=0,
        humidity=40,
        wind_speed=10.0,
        precipitation=0.0,
        precipitation_probability=0,
    )
    pw_b = TargetPeriodWeather(
        period_label="tomorrow",
        temperature=27.0,
        feels_like=28.0,
        condition="Partly cloudy",
        weather_code=2,
        humidity=60,
        wind_speed=12.0,
        precipitation=0.0,
        precipitation_probability=10,
    )

    res = comparison_engine_service.compare_locations(
        location_a=loc_a,
        location_b=loc_b,
        pw_a=pw_a,
        pw_b=pw_b,
        alerts_a=[],
        alerts_b=[],
        goal="warmer",
    )

    assert res.decision.recommended_key == "a"
    assert res.decision.recommended_location == "Delhi"
    assert "Delhi is warmer" in res.decision.summary
    assert "Delhi is warmer at 30.0°C compared with Mumbai at 27.0°C." in res.decision.winner_reason

    temp_factor = next(f for f in res.decision.factors if f.metric == "temperature")
    assert temp_factor.better_location == "a"
    assert "Delhi is warmer" in temp_factor.impact_note


def test_comparison_engine_travel_winner():
    """Verify deterministic comparison winner for travel goal when location A has lower rain chance."""
    loc_a = GeocodedLocationSchema(name="Kolkata", country="India", latitude=22.56, longitude=88.36, timezone="Asia/Kolkata")
    loc_b = GeocodedLocationSchema(name="Mumbai", country="India", latitude=19.07, longitude=72.87, timezone="Asia/Kolkata")

    pw_a = TargetPeriodWeather(
        period_label="tomorrow",
        temperature=28.0,
        feels_like=30.0,
        condition="Partly cloudy",
        weather_code=2,
        humidity=65,
        wind_speed=12.0,
        precipitation=0.0,
        precipitation_probability=10,
    )
    pw_b = TargetPeriodWeather(
        period_label="tomorrow",
        temperature=29.0,
        feels_like=34.0,
        condition="Heavy rain",
        weather_code=65,
        humidity=90,
        wind_speed=25.0,
        precipitation=18.0,
        precipitation_probability=85,
    )

    res = comparison_engine_service.compare_locations(
        location_a=loc_a,
        location_b=loc_b,
        pw_a=pw_a,
        pw_b=pw_b,
        alerts_a=[],
        alerts_b=[],
        goal="travel",
    )

    assert res.decision.recommended_key == "a"
    assert res.decision.recommended_location == "Kolkata"
    assert "Kolkata is the recommended choice" in res.decision.summary
    assert len(res.decision.factors) >= 4


def test_comparison_engine_broadly_similar():
    """Verify broadly similar conditions when metrics between both locations are very close."""
    loc_a = GeocodedLocationSchema(name="Kolkata", country="India", latitude=22.56, longitude=88.36, timezone="Asia/Kolkata")
    loc_b = GeocodedLocationSchema(name="Mumbai", country="India", latitude=19.07, longitude=72.87, timezone="Asia/Kolkata")

    pw_a = TargetPeriodWeather(
        period_label="today",
        temperature=26.0,
        feels_like=27.0,
        condition="Partly cloudy",
        weather_code=2,
        humidity=60,
        wind_speed=10.0,
        precipitation=0.0,
        precipitation_probability=10,
    )
    pw_b = TargetPeriodWeather(
        period_label="today",
        temperature=27.0,
        feels_like=28.0,
        condition="Clear sky",
        weather_code=0,
        humidity=58,
        wind_speed=12.0,
        precipitation=0.2,
        precipitation_probability=15,
    )

    res = comparison_engine_service.compare_locations(
        location_a=loc_a,
        location_b=loc_b,
        pw_a=pw_a,
        pw_b=pw_b,
        alerts_a=[],
        alerts_b=[],
        goal="general",
    )

    assert res.decision.recommended_key == "equal"
    assert res.decision.recommended_location == "Broadly Similar"
    assert "broadly similar" in res.decision.summary.lower()


@patch("app.services.query_service.geocoding_service.geocode_location")
@patch("app.services.weather_service.weather_service.get_current_weather")
@patch("app.services.weather_service.weather_service.get_forecast")
def test_comparison_chat_endpoint_full_flow(mock_forecast, mock_current, mock_geocode):
    """Verify POST /api/chat comparison query full orchestration."""
    test_session = "test_session_comparison_flow"
    SESSION_CONTEXT.pop(test_session, None)

    loc_a = GeocodedLocationSchema(name="Kolkata", country="India", latitude=22.56, longitude=88.36, timezone="Asia/Kolkata")
    loc_b = GeocodedLocationSchema(name="Mumbai", country="India", latitude=19.07, longitude=72.87, timezone="Asia/Kolkata")

    mock_geocode.side_effect = lambda loc_name: loc_a if "Kolkata" in loc_name else loc_b

    curr_a = CurrentWeatherResponse(
        location=LocationCoordinates(latitude=22.56, longitude=88.36, name="Kolkata", timezone="Asia/Kolkata"),
        current=CurrentWeather(temperature=25.0, feels_like=25.0, condition="Clear", weather_code=0, humidity=50, wind_speed=10.0, precipitation=0.0, precipitation_probability=10, time="2026-09-06T12:00"),
        source="open-meteo",
        timestamp="2026-09-06T12:00:00Z",
    )
    curr_b = CurrentWeatherResponse(
        location=LocationCoordinates(latitude=19.07, longitude=72.87, name="Mumbai", timezone="Asia/Kolkata"),
        current=CurrentWeather(temperature=30.0, feels_like=35.0, condition="Heavy Rain", weather_code=65, humidity=90, wind_speed=30.0, precipitation=15.0, precipitation_probability=80, time="2026-09-06T12:00"),
        source="open-meteo",
        timestamp="2026-09-06T12:00:00Z",
    )

    mock_current.side_effect = [curr_a, curr_b]
    mock_forecast.side_effect = [
        ForecastResponse(location=LocationCoordinates(latitude=22.56, longitude=88.36, name="Kolkata", timezone="Asia/Kolkata"), hourly=[HourlyForecast(time="2026-09-06T12:00", temperature=25.0, condition="Clear", weather_code=0, precipitation_probability=10, precipitation=0.0, wind_speed=10.0)], source="open-meteo", timestamp="2026-09-06T12:00:00Z"),
        ForecastResponse(location=LocationCoordinates(latitude=19.07, longitude=72.87, name="Mumbai", timezone="Asia/Kolkata"), hourly=[HourlyForecast(time="2026-09-06T12:00", temperature=30.0, condition="Heavy Rain", weather_code=65, precipitation_probability=80, precipitation=15.0, wind_speed=30.0)], source="open-meteo", timestamp="2026-09-06T12:00:00Z"),
    ]

    res = client.post("/api/chat", json={"message": "Compare Kolkata and Mumbai tomorrow", "session_id": test_session})
    assert res.status_code == 200
    data = res.json()

    assert data["query"]["intent"] == "comparison"
    assert data["comparison"] is not None
    assert data["comparison"]["location_a"]["name"] == "Kolkata"
    assert data["comparison"]["location_b"]["name"] == "Mumbai"
    assert data["comparison"]["decision"]["recommended_location"] == "Kolkata"


@patch("app.services.query_service.geocoding_service.geocode_location")
@patch("app.services.weather_service.weather_service.get_current_weather")
@patch("app.services.weather_service.weather_service.get_forecast")
def test_conversational_followup_comparison_context(mock_forecast, mock_current, mock_geocode):
    """Verify follow-up comparison query ('What about evening?') inherits dual locations."""
    test_session = "test_session_comp_followup"
    SESSION_CONTEXT.pop(test_session, None)

    loc_a = GeocodedLocationSchema(name="Kolkata", country="India", latitude=22.56, longitude=88.36, timezone="Asia/Kolkata")
    loc_b = GeocodedLocationSchema(name="Mumbai", country="India", latitude=19.07, longitude=72.87, timezone="Asia/Kolkata")

    mock_geocode.side_effect = lambda loc_name: loc_a if "Kolkata" in loc_name else loc_b

    curr = CurrentWeatherResponse(
        location=LocationCoordinates(latitude=22.56, longitude=88.36, name="Kolkata", timezone="Asia/Kolkata"),
        current=CurrentWeather(temperature=25.0, feels_like=25.0, condition="Clear", weather_code=0, humidity=50, wind_speed=10.0, precipitation=0.0, precipitation_probability=10, time="2026-09-06T12:00"),
        source="open-meteo",
        timestamp="2026-09-06T12:00:00Z",
    )
    mock_current.return_value = curr
    mock_forecast.return_value = ForecastResponse(
        location=LocationCoordinates(latitude=22.56, longitude=88.36, name="Kolkata", timezone="Asia/Kolkata"),
        hourly=[HourlyForecast(time="2026-09-06T12:00", temperature=25.0, condition="Clear", weather_code=0, precipitation_probability=10, precipitation=0.0, wind_speed=10.0)],
        source="open-meteo",
        timestamp="2026-09-06T12:00:00Z",
    )

    r1 = client.post("/api/chat", json={"message": "Compare Kolkata and Mumbai tomorrow", "session_id": test_session})
    assert r1.status_code == 200

    r2 = client.post("/api/chat", json={"message": "Which is better for outdoor activities?", "session_id": test_session})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["comparison"] is not None
    assert d2["comparison"]["location_a"]["name"] == "Kolkata"
    assert d2["comparison"]["location_b"]["name"] == "Mumbai"
    assert d2["comparison"]["comparison_goal"] == "outdoor_activity"


def test_missing_second_location_clarification():
    """Verify single location comparison query prompts for clarification."""
    test_session = "test_session_missing_loc_b"
    SESSION_CONTEXT.pop(test_session, None)

    res = client.post("/api/chat", json={"message": "Compare Kolkata", "session_id": test_session})
    assert res.status_code == 200
    data = res.json()
    assert data["needs_clarification"] is True
    assert "Which two locations" in data["summary"]


def test_weekend_and_specific_day_date_resolution():
    """Verify semantic date resolution for 'this weekend', 'this Saturday', and 'this Sunday' without falling back to today."""
    q_weekend = extract_query_entities_rule_based("Should I travel to Darjeeling or Kolkata this weekend?")
    assert q_weekend.intent == "comparison"
    assert q_weekend.extracted_location_a == "Darjeeling"
    assert q_weekend.extracted_location_b == "Kolkata"
    assert q_weekend.comparison_goal == "travel"
    assert q_weekend.date_context == "weekend"
    assert q_weekend.date_context != "today"

    q_comp_weekend = extract_query_entities_rule_based("Compare Kolkata and Mumbai this weekend.")
    assert q_comp_weekend.intent == "comparison"
    assert q_comp_weekend.extracted_location_a == "Kolkata"
    assert q_comp_weekend.extracted_location_b == "Mumbai"
    assert q_comp_weekend.date_context == "weekend"
    assert q_comp_weekend.date_context != "today"

    q_sat = extract_query_entities_rule_based("Compare Delhi and Mumbai this Saturday.")
    assert q_sat.intent == "comparison"
    assert q_sat.extracted_location_a == "Delhi"
    assert q_sat.extracted_location_b == "Mumbai"
    assert q_sat.date_context == "saturday"
    assert q_sat.date_context != "today"

    q_sun = extract_query_entities_rule_based("Compare Delhi and Mumbai this Sunday.")
    assert q_sun.intent == "comparison"
    assert q_sun.extracted_location_a == "Delhi"
    assert q_sun.extracted_location_b == "Mumbai"
    assert q_sun.date_context == "sunday"
    assert q_sun.date_context != "today"

