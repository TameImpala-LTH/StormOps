"""Comprehensive unit tests for severe weather alerts & risk advisory engine."""

import app.core.compat  # noqa: F401
from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.schemas.query import TargetPeriodWeather, GeocodedLocationSchema
from app.schemas.weather import CurrentWeatherResponse, LocationCoordinates, CurrentWeather, ForecastResponse, HourlyForecast
from app.services.alert_service import alert_engine_service
from app.services.llm_service import LLMService
from app.services.query_service import SESSION_CONTEXT

client = TestClient(app)


def test_alert_evaluation_thunderstorm():
    """Verify WMO code 95 triggers thunderstorm risk alert."""
    pw = TargetPeriodWeather(
        period_label="tomorrow evening",
        temperature=26.0,
        feels_like=29.0,
        condition="Thunderstorm with heavy rain",
        weather_code=95,
        humidity=90,
        wind_speed=35.0,
        precipitation=12.0,
        precipitation_probability=85,
    )
    alerts = alert_engine_service.evaluate_alerts(pw, "Kolkata, India")
    assert len(alerts) >= 1
    t_alert = next((a for a in alerts if a.category == "thunderstorm"), None)
    assert t_alert is not None
    assert t_alert.severity == "warning"
    assert "Thunderstorm Risk" in t_alert.title


def test_alert_evaluation_high_wind():
    """Verify wind speed 65 km/h triggers high wind warning."""
    pw = TargetPeriodWeather(
        period_label="today",
        temperature=18.0,
        feels_like=18.0,
        condition="Windy",
        weather_code=3,
        humidity=60,
        wind_speed=65.0,
        precipitation=0.0,
        precipitation_probability=10,
    )
    alerts = alert_engine_service.evaluate_alerts(pw, "Darjeeling, India")
    w_alert = next((a for a in alerts if a.category == "high_wind"), None)
    assert w_alert is not None
    assert w_alert.severity == "warning"
    assert "65.0 km/h" in w_alert.summary


def test_alert_evaluation_heavy_rain():
    """Verify precipitation 20 mm triggers heavy rain risk warning."""
    pw = TargetPeriodWeather(
        period_label="tomorrow",
        temperature=24.0,
        feels_like=26.0,
        condition="Heavy rain",
        weather_code=65,
        humidity=95,
        wind_speed=20.0,
        precipitation=20.0,
        precipitation_probability=90,
    )
    alerts = alert_engine_service.evaluate_alerts(pw, "Mumbai, India")
    r_alert = next((a for a in alerts if a.category == "heavy_rain"), None)
    assert r_alert is not None
    assert r_alert.severity == "warning"


def test_alert_evaluation_extreme_heat():
    """Verify temperature 40°C triggers extreme heat risk warning."""
    pw = TargetPeriodWeather(
        period_label="today afternoon",
        temperature=40.0,
        feels_like=44.0,
        condition="Clear sky",
        weather_code=0,
        humidity=30,
        wind_speed=15.0,
        precipitation=0.0,
        precipitation_probability=0,
    )
    alerts = alert_engine_service.evaluate_alerts(pw, "Delhi, India")
    h_alert = next((a for a in alerts if a.category == "extreme_heat"), None)
    assert h_alert is not None
    assert h_alert.severity == "warning"


def test_no_alert_for_mild_weather():
    """Verify mild pleasant weather returns empty alerts list."""
    pw = TargetPeriodWeather(
        period_label="today",
        temperature=22.0,
        feels_like=22.0,
        condition="Clear sky",
        weather_code=0,
        humidity=50,
        wind_speed=10.0,
        precipitation=0.0,
        precipitation_probability=10,
    )
    alerts = alert_engine_service.evaluate_alerts(pw, "Paris, France")
    assert len(alerts) == 0


def test_fog_advisory():
    """Verify WMO code 45 triggers dense fog risk advisory."""
    pw = TargetPeriodWeather(
        period_label="tomorrow morning",
        temperature=8.0,
        feels_like=8.0,
        condition="Fog",
        weather_code=45,
        humidity=98,
        wind_speed=5.0,
        precipitation=0.0,
        precipitation_probability=10,
    )
    alerts = alert_engine_service.evaluate_alerts(pw, "London, UK")
    f_alert = next((a for a in alerts if a.category == "fog"), None)
    assert f_alert is not None
    assert f_alert.severity == "advisory"
    assert "Dense Fog Risk" in f_alert.title


def test_exact_rain_probability_threshold_behavior():
    """Verify precip_prob >= 60% with 1.5mm precip triggers watch."""
    pw = TargetPeriodWeather(
        period_label="today",
        temperature=25.0,
        feels_like=25.0,
        condition="Moderate rain",
        weather_code=61,
        humidity=80,
        wind_speed=12.0,
        precipitation=1.5,
        precipitation_probability=60,
    )
    alerts = alert_engine_service.evaluate_alerts(pw, "Kolkata, India")
    r_alert = next((a for a in alerts if a.category == "heavy_rain"), None)
    assert r_alert is not None
    assert r_alert.severity == "watch"


def test_no_false_alert_below_thresholds():
    """Verify precip_prob=50% with 0.5mm precip does NOT trigger heavy rain watch or warning."""
    pw = TargetPeriodWeather(
        period_label="today",
        temperature=25.0,
        feels_like=25.0,
        condition="Light drizzle",
        weather_code=51,
        humidity=70,
        wind_speed=10.0,
        precipitation=0.5,
        precipitation_probability=50,
    )
    alerts = alert_engine_service.evaluate_alerts(pw, "Kolkata, India")
    r_alert = next((a for a in alerts if a.category == "heavy_rain"), None)
    assert r_alert is None


def test_multiple_simultaneous_alerts():
    """Verify multiple severe conditions (thunderstorm + 65 km/h wind) return multiple alerts."""
    pw = TargetPeriodWeather(
        period_label="tomorrow evening",
        temperature=28.0,
        feels_like=32.0,
        condition="Thunderstorm with heavy rain",
        weather_code=95,
        humidity=90,
        wind_speed=65.0,
        precipitation=18.0,
        precipitation_probability=95,
    )
    alerts = alert_engine_service.evaluate_alerts(pw, "Kolkata, India")
    categories = [a.category for a in alerts]
    assert "thunderstorm" in categories
    assert "heavy_rain" in categories
    assert "high_wind" in categories


@patch("app.services.query_service.geocoding_service.geocode_location")
@patch("app.services.weather_service.weather_service.get_current_weather")
@patch("app.services.weather_service.weather_service.get_forecast")
def test_conversational_followup_retains_alerts(mock_forecast, mock_current, mock_geocode):
    """Verify conversational follow-up query retains target period and severe weather alerts."""
    test_session = "test_session_alert_followup"
    SESSION_CONTEXT.pop(test_session, None)

    mock_geocode.return_value = GeocodedLocationSchema(
        name="Kolkata", country="India", admin1="West Bengal", latitude=22.56, longitude=88.36, timezone="Asia/Kolkata"
    )
    mock_current.return_value = CurrentWeatherResponse(
        location=LocationCoordinates(latitude=22.56, longitude=88.36, name="Kolkata", timezone="Asia/Kolkata"),
        current=CurrentWeather(temperature=30.0, feels_like=34.0, condition="Thunderstorm", weather_code=95, humidity=88, wind_speed=50.0, precipitation=15.0, precipitation_probability=90, time="2026-09-06T12:00"),
        source="open-meteo",
        timestamp="2026-09-06T12:00:00Z",
    )
    mock_forecast.return_value = ForecastResponse(
        location=LocationCoordinates(latitude=22.56, longitude=88.36, name="Kolkata", timezone="Asia/Kolkata"),
        hourly=[
            HourlyForecast(time="2026-09-06T12:00", temperature=30.0, condition="Thunderstorm", weather_code=95, precipitation_probability=90, precipitation=15.0, wind_speed=50.0)
        ],
        source="open-meteo",
        timestamp="2026-09-06T12:00:00Z",
    )

    r1 = client.post("/api/chat", json={"message": "Will it rain tomorrow in Kolkata?", "session_id": test_session})
    assert r1.status_code == 200
    d1 = r1.json()
    assert len(d1["alerts"]) >= 1

    r2 = client.post("/api/chat", json={"message": "What about evening?", "session_id": test_session})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["location"]["name"] == "Kolkata"
    assert len(d2["alerts"]) >= 1


@patch("app.services.query_service.geocoding_service.geocode_location")
@patch("app.services.weather_service.weather_service.get_current_weather")
@patch("app.services.weather_service.weather_service.get_forecast")
def test_location_change_updates_alerts(mock_forecast, mock_current, mock_geocode):
    """Verify location change (Kolkata severe -> Paris mild) clears severe alerts."""
    test_session = "test_session_alert_locchange"
    SESSION_CONTEXT.pop(test_session, None)

    mock_kolkata = GeocodedLocationSchema(name="Kolkata", country="India", latitude=22.56, longitude=88.36, timezone="Asia/Kolkata")
    mock_paris = GeocodedLocationSchema(name="Paris", country="France", latitude=48.85, longitude=2.35, timezone="Europe/Paris")

    mock_geocode.side_effect = lambda loc_name: mock_kolkata if "Kolkata" in loc_name else mock_paris

    # Kolkata severe
    curr_severe = CurrentWeatherResponse(
        location=LocationCoordinates(latitude=22.56, longitude=88.36, name="Kolkata", timezone="Asia/Kolkata"),
        current=CurrentWeather(temperature=30.0, feels_like=34.0, condition="Thunderstorm", weather_code=95, humidity=88, wind_speed=50.0, precipitation=15.0, precipitation_probability=90, time="2026-09-06T12:00"),
        source="open-meteo",
        timestamp="2026-09-06T12:00:00Z",
    )
    # Paris mild
    curr_mild = CurrentWeatherResponse(
        location=LocationCoordinates(latitude=48.85, longitude=2.35, name="Paris", timezone="Europe/Paris"),
        current=CurrentWeather(temperature=20.0, feels_like=20.0, condition="Clear sky", weather_code=0, humidity=50, wind_speed=10.0, precipitation=0.0, precipitation_probability=5, time="2026-09-06T12:00"),
        source="open-meteo",
        timestamp="2026-09-06T12:00:00Z",
    )

    mock_current.side_effect = [curr_severe, curr_mild]
    mock_forecast.side_effect = [
        ForecastResponse(location=LocationCoordinates(latitude=22.56, longitude=88.36, name="Kolkata", timezone="Asia/Kolkata"), hourly=[HourlyForecast(time="2026-09-06T12:00", temperature=30.0, condition="Thunderstorm", weather_code=95, precipitation_probability=90, precipitation=15.0, wind_speed=50.0)], source="open-meteo", timestamp="2026-09-06T12:00:00Z"),
        ForecastResponse(location=LocationCoordinates(latitude=48.85, longitude=2.35, name="Paris", timezone="Europe/Paris"), hourly=[HourlyForecast(time="2026-09-06T12:00", temperature=20.0, condition="Clear sky", weather_code=0, precipitation_probability=5, precipitation=0.0, wind_speed=10.0)], source="open-meteo", timestamp="2026-09-06T12:00:00Z"),
    ]

    r1 = client.post("/api/chat", json={"message": "What's the weather in Kolkata?", "session_id": test_session})
    assert len(r1.json()["alerts"]) >= 1

    r2 = client.post("/api/chat", json={"message": "What about Paris?", "session_id": test_session})
    assert len(r2.json()["alerts"]) == 0


@patch("app.services.query_service.geocoding_service.geocode_location")
@patch("app.services.weather_service.weather_service.get_current_weather")
@patch("app.services.weather_service.weather_service.get_forecast")
def test_llm_unavailable_returns_deterministic_alerts(mock_forecast, mock_current, mock_geocode):
    """Verify deterministic alerts are returned even when LLM is unconfigured."""
    test_session = "test_session_no_llm"
    SESSION_CONTEXT.pop(test_session, None)

    mock_geocode.return_value = GeocodedLocationSchema(
        name="Kolkata", country="India", latitude=22.56, longitude=88.36, timezone="Asia/Kolkata"
    )
    mock_current.return_value = CurrentWeatherResponse(
        location=LocationCoordinates(latitude=22.56, longitude=88.36, name="Kolkata", timezone="Asia/Kolkata"),
        current=CurrentWeather(temperature=30.0, feels_like=34.0, condition="Thunderstorm", weather_code=95, humidity=88, wind_speed=50.0, precipitation=15.0, precipitation_probability=90, time="2026-09-06T12:00"),
        source="open-meteo",
        timestamp="2026-09-06T12:00:00Z",
    )
    mock_forecast.return_value = ForecastResponse(
        location=LocationCoordinates(latitude=22.56, longitude=88.36, name="Kolkata", timezone="Asia/Kolkata"),
        hourly=[
            HourlyForecast(time="2026-09-06T12:00", temperature=30.0, condition="Thunderstorm", weather_code=95, precipitation_probability=90, precipitation=15.0, wind_speed=50.0)
        ],
        source="open-meteo",
        timestamp="2026-09-06T12:00:00Z",
    )

    with patch.object(LLMService, "is_configured", False):
        res = client.post("/api/chat", json={"message": "What's the weather in Kolkata?", "session_id": test_session})
        assert res.status_code == 200
        data = res.json()
        assert "alerts" in data
        assert len(data["alerts"]) >= 1
