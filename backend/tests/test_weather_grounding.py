"""Tests for WeatherGPT Grounding, temporal contracts, and WeatherPeriodInfo invariants."""

import sys
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from app.core.compat import *  # noqa: F401,F403

from app.schemas.query import (
    ExtractedQueryInfo,
    GeocodedLocationSchema,
    QueryRequest,
    QueryResponse,
    TargetPeriodWeather,
    WeatherPeriodInfo,
)
from app.schemas.weather import CurrentWeather, HourlyForecast
from app.services.decision_service import decision_engine_service
from app.services.query_service import query_service


class TestWeatherGroundingContract:
    """Test the WeatherPeriodInfo contract and grounding invariants."""

    def test_weather_period_info_schema(self):
        """WeatherPeriodInfo initializes with expected attributes."""
        info = WeatherPeriodInfo(
            type="tomorrow",
            label="Tomorrow",
            date="2026-09-22",
            is_forecast=True,
        )
        assert info.type == "tomorrow"
        assert info.label == "Tomorrow"
        assert info.date == "2026-09-22"
        assert info.is_forecast is True

    def test_query_response_includes_period_schema(self):
        """QueryResponse schema accepts period: Optional[WeatherPeriodInfo]."""
        q_info = ExtractedQueryInfo(
            original_query="Weather tomorrow in Kolkata",
            intent="weather_information",
            extracted_location="Kolkata",
            date_context="tomorrow",
            time_period="current",
            language="en",
        )
        period_info = WeatherPeriodInfo(
            type="tomorrow",
            label="Tomorrow",
            date="2026-09-22",
            is_forecast=True,
        )
        resp = QueryResponse(
            query=q_info,
            location=None,
            current=None,
            period=period_info,
            period_weather=None,
            period_forecast=[],
            forecast=[],
            decision=None,
            alerts=[],
            summary="Tomorrow weather forecast in Kolkata",
            needs_clarification=False,
            language="en",
            session_id="test-session",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        assert resp.period is not None
        assert resp.period.type == "tomorrow"
        assert resp.period.is_forecast is True

    def test_filter_forecast_calculates_period_average_humidity(self):
        """filter_forecast_by_period calculates the average relative humidity of period matching items."""
        curr = CurrentWeather(
            temperature=30.0,
            feels_like=35.0,
            condition="Clear",
            weather_code=0,
            humidity=80,
            wind_speed=10.0,
            precipitation=0.0,
            precipitation_probability=0,
            time="2026-09-21T12:00:00Z",
        )
        # Create hourly forecast with tomorrow date and specific humidities (e.g. 50, 60, 70 -> avg 60)
        hourly_items = [
            HourlyForecast(
                time="2026-09-22T08:00:00Z",
                temperature=28.0,
                feels_like=30.0,
                condition="Partly cloudy",
                weather_code=1,
                precipitation=0.0,
                precipitation_probability=10,
                wind_speed=8.0,
                humidity=50,
            ),
            HourlyForecast(
                time="2026-09-22T12:00:00Z",
                temperature=32.0,
                feels_like=36.0,
                condition="Partly cloudy",
                weather_code=1,
                precipitation=0.0,
                precipitation_probability=20,
                wind_speed=12.0,
                humidity=60,
            ),
            HourlyForecast(
                time="2026-09-22T16:00:00Z",
                temperature=29.0,
                feels_like=32.0,
                condition="Partly cloudy",
                weather_code=1,
                precipitation=0.0,
                precipitation_probability=15,
                wind_speed=10.0,
                humidity=70,
            ),
        ]
        metrics = decision_engine_service.filter_forecast_by_period(
            current=curr,
            forecast=hourly_items,
            date_context="tomorrow",
            time_period="current",
        )
        # 50 + 60 + 70 / 3 = 60
        assert metrics.humidity == 60
        assert metrics.period_label == "tomorrow"
        assert metrics.has_missing_data is False

    def test_period_weather_missing_data_invariant(self):
        """When forecast data for requested weekend is missing, has_missing_data is True."""
        curr = CurrentWeather(
            temperature=30.0,
            feels_like=35.0,
            condition="Clear",
            weather_code=0,
            humidity=80,
            wind_speed=10.0,
            precipitation=0.0,
            precipitation_probability=0,
            time="2026-09-21T12:00:00Z",
        )
        # Only provides today items (weekday Monday = 0), weekend is 5 days ahead and missing
        today_items = [
            HourlyForecast(
                time="2026-09-21T08:00:00Z",
                temperature=28.0,
                condition="Clear",
                weather_code=0,
                precipitation=0.0,
                wind_speed=5.0,
            )
        ]
        metrics = decision_engine_service.filter_forecast_by_period(
            current=curr,
            forecast=today_items,
            date_context="weekend",
            time_period="current",
        )
        assert metrics.has_missing_data is True
        assert metrics.condition == "Forecast unavailable"

    @pytest.mark.asyncio
    async def test_process_natural_query_tomorrow_grounding(self):
        """Verify tomorrow query populates period and sanitizes LLM payload."""
        req = QueryRequest(message="What is the weather in Kolkata tomorrow?")

        geocoded = GeocodedLocationSchema(
            name="Kolkata, West Bengal, India",
            country="India",
            country_code="IN",
            admin1="West Bengal",
            latitude=22.5726,
            longitude=88.3639,
            timezone="Asia/Kolkata",
        )

        curr = CurrentWeather(
            temperature=29.0,
            feels_like=33.0,
            condition="Haze",
            weather_code=5,
            humidity=75,
            wind_speed=6.0,
            precipitation=0.0,
            precipitation_probability=10,
            time="2026-09-21T14:00:00Z",
        )

        hourly = [
            HourlyForecast(
                time="2026-09-22T08:00:00Z",
                temperature=27.0,
                feels_like=30.0,
                condition="Partly cloudy",
                weather_code=1,
                precipitation=0.0,
                precipitation_probability=20,
                wind_speed=8.0,
                humidity=65,
            ),
            HourlyForecast(
                time="2026-09-22T14:00:00Z",
                temperature=32.0,
                feels_like=36.0,
                condition="Rain",
                weather_code=61,
                precipitation=2.5,
                precipitation_probability=85,
                wind_speed=14.0,
                humidity=78,
            ),
        ]

        from app.schemas.weather import CurrentWeatherResponse, ForecastResponse, LocationCoordinates
        mock_curr_res = CurrentWeatherResponse(
            location=LocationCoordinates(latitude=22.57, longitude=88.36),
            current=curr,
            source="open-meteo",
            timestamp="2026-09-21T14:00:00Z",
        )
        mock_forecast_res = ForecastResponse(
            location=LocationCoordinates(latitude=22.57, longitude=88.36),
            hourly=hourly,
            source="open-meteo",
            timestamp="2026-09-21T14:00:00Z",
        )

        captured_llm_payload = {}

        async def fake_grounded_response(*args, **kwargs):
            nonlocal captured_llm_payload
            captured_llm_payload = kwargs.get("weather_summary_data", {})
            return "Tomorrow in Kolkata, expect partly cloudy skies turning into afternoon rain with a high of 32°C."

        with patch("app.services.geocoding_service.geocoding_service.geocode_location", new_callable=AsyncMock) as mock_geo, \
             patch("app.services.weather_service.weather_service.get_weather_bundle", new_callable=AsyncMock) as mock_bundle, \
             patch("app.services.llm_service.LLMService.is_configured", new_callable=PropertyMock, return_value=True), \
             patch("app.services.llm_service.llm_service.generate_grounded_response", side_effect=fake_grounded_response):

            mock_geo.return_value = geocoded
            mock_bundle.return_value = (mock_curr_res, mock_forecast_res)

            resp = await query_service.process_query(req.message, session_id="test_session_grounding")

            assert resp.period is not None
            assert resp.period.type == "tomorrow"
            assert resp.period.is_forecast is True
            assert resp.period.label.lower() == "tomorrow"
            assert resp.period_weather is not None
            assert resp.period_weather.precipitation_probability == 85

            # LLM payload verification
            assert captured_llm_payload.get("is_forecast") is True
            assert str(captured_llm_payload.get("target_period")).lower() == "tomorrow"
            # Crucial invariant: observation_time from today must NOT be passed for a future forecast
            assert "observation_time" not in captured_llm_payload
            assert "forecast_period" in captured_llm_payload

    @pytest.mark.asyncio
    async def test_rejection_of_llm_unavailable_apology_when_structured_data_exists(self):
        """When structured weather data exists, LLM apology must be rejected and replaced."""
        req = QueryRequest(message="What is the weather in Kolkata tomorrow?")

        geocoded = GeocodedLocationSchema(
            name="Kolkata, West Bengal, India",
            country="India",
            country_code="IN",
            admin1="West Bengal",
            latitude=22.5726,
            longitude=88.3639,
            timezone="Asia/Kolkata",
        )

        curr = CurrentWeather(
            temperature=29.0,
            feels_like=34.0,
            condition="Partly cloudy",
            weather_code=1,
            humidity=70,
            wind_speed=8.6,
            precipitation=1.39,
            precipitation_probability=98,
            time="2026-09-21T14:00:00Z",
        )

        hourly = [
            HourlyForecast(
                time="2026-09-22T14:00:00Z",
                temperature=29.0,
                feels_like=34.0,
                condition="Light rain",
                weather_code=61,
                precipitation=1.39,
                precipitation_probability=98,
                wind_speed=8.6,
                humidity=70,
            )
        ]

        from app.schemas.weather import CurrentWeatherResponse, ForecastResponse, LocationCoordinates
        mock_curr_res = CurrentWeatherResponse(
            location=LocationCoordinates(latitude=22.57, longitude=88.36),
            current=curr,
            source="open-meteo",
            timestamp="2026-09-21T14:00:00Z",
        )
        mock_forecast_res = ForecastResponse(
            location=LocationCoordinates(latitude=22.57, longitude=88.36),
            hourly=hourly,
            source="open-meteo",
            timestamp="2026-09-21T14:00:00Z",
        )

        # Simulate LLM returning the exact problematic apology from the user's screenshot
        async def fake_apologetic_llm(*args, **kwargs):
            return "I'm sorry, but the weather data for tomorrow in Kolkata is not available in the information I have."

        with patch("app.services.geocoding_service.geocoding_service.geocode_location", new_callable=AsyncMock) as mock_geo, \
             patch("app.services.weather_service.weather_service.get_weather_bundle", new_callable=AsyncMock) as mock_bundle, \
             patch("app.services.llm_service.LLMService.is_configured", new_callable=PropertyMock, return_value=True), \
             patch("app.services.llm_service.llm_service.generate_grounded_response", side_effect=fake_apologetic_llm):

            mock_geo.return_value = geocoded
            mock_bundle.return_value = (mock_curr_res, mock_forecast_res)

            resp = await query_service.process_query(req.message, session_id="test_apology_rejection")

            # Invariant 1: structured data exists
            assert resp.period_weather is not None
            assert resp.period_weather.temperature == 29.0
            assert resp.period_weather.precipitation_probability == 98

            # Invariant 2: Apology is strictly rejected
            assert "i'm sorry" not in resp.summary.lower()
            assert "not available" not in resp.summary.lower()

            # Invariant 3: Rich detailed interpretation is generated from structured metrics
            assert "29" in resp.summary
            assert "34" in resp.summary or "feels like" in resp.summary.lower()

            # Invariant 4: Key insight is concise and distinct
            assert resp.key_insight is not None
            assert len(resp.key_insight) > 10
            assert resp.key_insight != resp.summary

