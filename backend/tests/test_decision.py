"""Unit tests for WeatherGPT Decision Engine service and structured decision response schema."""

import app.core.compat  # noqa: F401 — must be imported before FastAPI/pydantic

from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.schemas.query import ExtractedQueryInfo, GeocodedLocationSchema
from app.schemas.weather import (
    CurrentWeather,
    CurrentWeatherResponse,
    ForecastResponse,
    HourlyForecast,
    LocationCoordinates,
)
from app.services.decision_service import decision_engine_service

client = TestClient(app)

# Helper mock current weather creator
def make_mock_current(temp=25.0, precip_prob=10, precip=0.0, code=0, wind=10.0) -> CurrentWeather:
    return CurrentWeather(
        temperature=temp,
        feels_like=temp + 1.0,
        condition="Clear sky" if code == 0 else "Rain",
        weather_code=code,
        humidity=60,
        wind_speed=wind,
        precipitation=precip,
        precipitation_probability=precip_prob,
        time="2026-09-06T12:00",
    )


def test_period_selection_tomorrow_evening():
    """Verify period forecast filtering correctly extracts tomorrow evening forecast slice."""
    curr = make_mock_current(temp=25.0, precip_prob=0, precip=0.0)
    # Forecast across today and tomorrow
    hourly = [
        HourlyForecast(time="2026-09-06T12:00", temperature=25.0, condition="Clear", weather_code=0, precipitation_probability=0, precipitation=0.0, wind_speed=5.0),
        HourlyForecast(time="2026-09-07T18:00", temperature=28.0, condition="Moderate rain", weather_code=61, precipitation_probability=85, precipitation=4.0, wind_speed=12.0),
    ]

    q_info = ExtractedQueryInfo(
        original_query="Should I carry an umbrella in Kolkata tomorrow evening?",
        intent="umbrella_recommendation",
        extracted_location="Kolkata",
        date_context="tomorrow",
        time_period="evening",
    )

    res = decision_engine_service.evaluate_decision(q_info, curr, hourly)
    assert res.type == "umbrella"
    assert res.recommendation == "recommended"
    assert "tomorrow evening" in res.summary
    assert any(f.metric == "precipitation_probability" and f.value == "85%" for f in res.factors)


def test_period_selection_tonight():
    """Verify period forecast filtering for tonight."""
    curr = make_mock_current(temp=25.0)
    hourly = [
        HourlyForecast(time="2026-09-06T12:00", temperature=25.0, condition="Clear", weather_code=0, precipitation_probability=0, precipitation=0.0, wind_speed=5.0),
        HourlyForecast(time="2026-09-06T22:00", temperature=8.0, condition="Clear", weather_code=0, precipitation_probability=5, precipitation=0.0, wind_speed=15.0),
    ]

    q_info = ExtractedQueryInfo(
        original_query="Do I need a jacket in Darjeeling tonight?",
        intent="clothing_recommendation",
        extracted_location="Darjeeling",
        date_context="today",
        time_period="tonight",
    )

    res = decision_engine_service.evaluate_decision(q_info, curr, hourly)
    assert res.type == "clothing"
    assert res.recommendation == "recommended"
    assert "tonight" in res.summary
    assert any(f.metric == "temperature" and f.value == "8.0°C" for f in res.factors)


def test_period_selection_tomorrow():
    """Verify period forecast filtering for all day tomorrow."""
    curr = make_mock_current(temp=25.0)
    hourly = [
        HourlyForecast(time="2026-09-06T12:00", temperature=25.0, condition="Clear", weather_code=0, precipitation_probability=0, precipitation=0.0, wind_speed=5.0),
        HourlyForecast(time="2026-09-07T14:00", temperature=32.0, condition="Thunderstorm", weather_code=95, precipitation_probability=90, precipitation=10.0, wind_speed=38.0),
    ]

    q_info = ExtractedQueryInfo(
        original_query="Should I postpone my outdoor plan in Mumbai tomorrow?",
        intent="outdoor_activity_recommendation",
        extracted_location="Mumbai",
        date_context="tomorrow",
        time_period="current",
    )

    res = decision_engine_service.evaluate_decision(q_info, curr, hourly)
    assert res.type == "outdoor_activity"
    assert res.recommendation == "not_recommended"
    assert "tomorrow" in res.summary


def test_umbrella_high_and_low_rain_probability():
    """Verify umbrella decision rules for high vs low rain probability."""
    # High rain prob
    curr_high = make_mock_current(precip_prob=80, precip=3.0, code=61)
    q_info = ExtractedQueryInfo(original_query="Should I carry an umbrella?", intent="umbrella_recommendation")
    res_high = decision_engine_service.evaluate_decision(q_info, curr_high)
    assert res_high.recommendation == "recommended"

    # Low rain prob
    curr_low = make_mock_current(precip_prob=5, precip=0.0, code=0)
    res_low = decision_engine_service.evaluate_decision(q_low:=q_info, curr_low)
    assert res_low.recommendation == "not_recommended"


def test_outdoor_activity_strong_wind():
    """Verify outdoor activity returns caution/not_recommended for strong wind."""
    curr_wind = make_mock_current(temp=22.0, precip_prob=0, code=0, wind=38.0)
    q_info = ExtractedQueryInfo(original_query="Is it safe for an outdoor event?", intent="outdoor_activity_recommendation")

    res = decision_engine_service.evaluate_decision(q_info, curr_wind)
    assert res.type == "outdoor_activity"
    assert res.recommendation == "not_recommended"
    assert any(f.metric == "wind_speed" and f.value == "38.0 km/h" for f in res.factors)


def test_travel_decision_severe_weather():
    """Verify travel safety decision evaluation."""
    curr_fog = make_mock_current(code=45, wind=15.0)
    q_travel = ExtractedQueryInfo(original_query="Is it safe to travel tonight?", intent="travel_recommendation")

    res = decision_engine_service.evaluate_decision(q_travel, curr_fog)
    assert res.type == "travel"
    assert res.recommendation == "caution"


def test_clothing_temperature_bands():
    """Verify clothing jacket recommendations based on temperature."""
    # Cold weather (8°C)
    curr_cold = make_mock_current(temp=8.0)
    q_coat = ExtractedQueryInfo(original_query="Do I need a jacket?", intent="clothing_recommendation")
    res_cold = decision_engine_service.evaluate_decision(q_coat, curr_cold)
    assert res_cold.type == "clothing"
    assert res_cold.recommendation == "recommended"

    # Warm weather (26°C)
    curr_warm = make_mock_current(temp=26.0)
    res_warm = decision_engine_service.evaluate_decision(q_coat, curr_warm)
    assert res_warm.type == "clothing"
    assert res_warm.recommendation == "neutral"


def test_missing_required_data_handling():
    """Verify missing required weather data returns recommendation = 'unknown'."""
    invalid_curr = CurrentWeather(
        temperature=None,
        feels_like=None,
        condition="Unknown",
        weather_code=0,
        humidity=50,
        wind_speed=None,
        precipitation=None,
        time="2026-09-06T12:00",
    )
    q_info = ExtractedQueryInfo(original_query="Should I carry an umbrella?", intent="umbrella_recommendation")
    res = decision_engine_service.evaluate_decision(q_info, invalid_curr)
    assert res.recommendation == "unknown"
    assert res.confidence == "low"


def test_normal_weather_query_has_no_decision_object():
    """Verify normal weather information queries return None for decision object."""
    curr = make_mock_current(temp=22.0)
    q_info = ExtractedQueryInfo(original_query="What is the weather in Kolkata?", intent="weather_information")
    res = decision_engine_service.evaluate_decision(q_info, curr)
    assert res is None


def test_period_selection_tonight_crosses_midnight():
    """Verify tonight time window correctly includes hours from 21:00 on target date through 04:00 next day."""
    curr = make_mock_current(temp=25.0)
    hourly = [
        HourlyForecast(time="2026-09-06T15:00", temperature=30.0, condition="Clear", weather_code=0, precipitation_probability=0, precipitation=0.0, wind_speed=5.0),
        HourlyForecast(time="2026-09-06T21:00", temperature=24.0, condition="Clear", weather_code=0, precipitation_probability=0, precipitation=0.0, wind_speed=5.0),
        HourlyForecast(time="2026-09-06T23:00", temperature=22.0, condition="Clear", weather_code=0, precipitation_probability=0, precipitation=0.0, wind_speed=5.0),
        # Following day early morning hours (00:00 to 04:00):
        HourlyForecast(time="2026-09-07T01:00", temperature=20.0, condition="Clear", weather_code=0, precipitation_probability=0, precipitation=0.0, wind_speed=5.0),
        HourlyForecast(time="2026-09-07T03:00", temperature=19.0, condition="Clear", weather_code=0, precipitation_probability=0, precipitation=0.0, wind_speed=5.0),
        HourlyForecast(time="2026-09-07T08:00", temperature=26.0, condition="Clear", weather_code=0, precipitation_probability=0, precipitation=0.0, wind_speed=5.0),
    ]

    metrics = decision_engine_service.filter_forecast_by_period(
        current=curr,
        forecast=hourly,
        date_context="today",
        time_period="tonight",
    )

    times = [item.time for item in metrics.matching_items]
    assert "2026-09-06T21:00" in times
    assert "2026-09-06T23:00" in times
    assert "2026-09-07T01:00" in times
    assert "2026-09-07T03:00" in times
    assert "2026-09-06T15:00" not in times
    assert "2026-09-07T08:00" not in times
    assert len(metrics.matching_items) == 4


def test_dominant_condition_isolated_rain_spike():
    """Verify that an isolated 1-hour drizzle spike on a full clear day does not mislabel the day condition as rainy."""
    curr = make_mock_current(temp=25.0)
    # 24 hours: 23 hours Clear sky (code 0), 1 hour Light drizzle (code 51, 0.2mm, 55% prob)
    hourly = []
    for h in range(24):
        time_str = f"2026-09-06T{h:02d}:00"
        if h == 14:
            hourly.append(HourlyForecast(time=time_str, temperature=28.0, condition="Light drizzle", weather_code=51, precipitation_probability=55, precipitation=0.2, wind_speed=10.0))
        else:
            hourly.append(HourlyForecast(time=time_str, temperature=25.0, condition="Clear sky", weather_code=0, precipitation_probability=0, precipitation=0.0, wind_speed=8.0))

    metrics = decision_engine_service.filter_forecast_by_period(
        current=curr,
        forecast=hourly,
        date_context="today",
        time_period="all",
    )

    # Dominant condition should remain Clear sky
    assert metrics.weather_code == 0
    assert metrics.condition == "Clear sky"
    # But peak probability must faithfully reflect the 55% risk
    assert metrics.precipitation_probability == 55
    assert metrics.precipitation == 0.2


def test_sustained_rain_updates_period_condition():
    """Verify that sustained rain (>= 3 hours) correctly updates the period condition to rain."""
    curr = make_mock_current(temp=22.0)
    hourly = []
    for h in range(24):
        time_str = f"2026-09-06T{h:02d}:00"
        if 13 <= h <= 16:  # 4 hours of rain
            hourly.append(HourlyForecast(time=time_str, temperature=22.0, condition="Moderate rain", weather_code=61, precipitation_probability=80, precipitation=1.5, wind_speed=14.0))
        else:
            hourly.append(HourlyForecast(time=time_str, temperature=24.0, condition="Clear sky", weather_code=0, precipitation_probability=5, precipitation=0.0, wind_speed=8.0))

    metrics = decision_engine_service.filter_forecast_by_period(
        current=curr,
        forecast=hourly,
        date_context="today",
        time_period="all",
    )

    # Sustained rain should be adopted as the warning condition
    assert metrics.weather_code == 61
    assert metrics.condition == "Moderate rain"
    assert metrics.precipitation_probability == 80


def test_period_feels_like_and_rain_duration():
    """Verify PeriodWeatherMetrics uses provider-supplied hourly apparent temperatures and calculates rain duration."""
    curr = make_mock_current(temp=30.0)
    hourly = []
    for h in range(12):
        time_str = f"2026-09-06T{h+6:02d}:00"
        hourly.append(
            HourlyForecast(
                time=time_str,
                temperature=30.0,
                feels_like=36.0,  # Hot humid conditions
                condition="Partly cloudy" if h != 8 else "Light rain",
                weather_code=2 if h != 8 else 61,
                precipitation_probability=10 if h != 8 else 70,
                precipitation=0.0 if h != 8 else 1.2,
                wind_speed=12.0,
            )
        )

    metrics = decision_engine_service.filter_forecast_by_period(
        current=curr,
        forecast=hourly,
        date_context="today",
        time_period="all",
    )

    # Feels-like should reflect apparent temperatures (36.0), not raw air temp (30.0)
    assert metrics.feels_like == 36.0
    assert metrics.temperature == 30.0
    # Exactly 1 hour of rain meets the criteria (h=8)
    assert metrics.rain_duration_hours == 1
    assert metrics.precipitation_probability == 70
    assert metrics.peak_hour == "afternoon"  # h=8 corresponds to 14:00


