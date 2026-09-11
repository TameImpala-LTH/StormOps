"""Comprehensive unit tests for session context, missing location clarification, LLM integration, and chat endpoints."""

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
from app.services.llm_service import LLMService
from app.services.query_service import SESSION_CONTEXT, extract_query_entities_rule_based

client = TestClient(app)

MOCK_DARJEELING = GeocodedLocationSchema(
    name="Darjeeling",
    country="India",
    admin1="West Bengal",
    latitude=27.03333,
    longitude=88.26667,
    timezone="Asia/Kolkata",
)

MOCK_PARIS = GeocodedLocationSchema(
    name="Paris",
    country="France",
    admin1="Ile-de-France",
    latitude=48.85341,
    longitude=2.3488,
    timezone="Europe/Paris",
)

MOCK_CURRENT = CurrentWeatherResponse(
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

MOCK_FORECAST = ForecastResponse(
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


def test_rule_based_missing_location_extraction():
    """Verify rule-based parser returns None for location when query has no location."""
    res = extract_query_entities_rule_based("Should I carry an umbrella tomorrow?")
    assert res.intent == "umbrella_recommendation"
    assert res.extracted_location is None
    assert res.date_context == "tomorrow"


@patch("app.services.query_service.geocoding_service.geocode_location")
@patch("app.services.weather_service.weather_service.get_current_weather")
@patch("app.services.weather_service.weather_service.get_forecast")
def test_missing_location_clarification_response(mock_forecast, mock_current, mock_geocode):
    """Test 1: Missing location without session context returns clarification response."""
    test_session = "test_session_missing_loc"
    SESSION_CONTEXT.pop(test_session, None)

    response = client.post("/api/chat", json={"message": "Should I carry an umbrella tomorrow?", "session_id": test_session})
    assert response.status_code == 200

    data = response.json()
    assert data["needs_clarification"] is True
    assert "Which location should I check the weather for?" in data["summary"]
    assert data["location"] is None
    assert data["current"] is None


@patch("app.services.query_service.geocoding_service.geocode_location")
@patch("app.services.weather_service.weather_service.get_current_weather")
@patch("app.services.weather_service.weather_service.get_forecast")
def test_session_context_followup_and_override(mock_forecast, mock_current, mock_geocode):
    """Test 2 & 3: Contextual follow-up reuses session location; explicit new location overrides context."""
    test_session = "test_session_context_flow"
    SESSION_CONTEXT.pop(test_session, None)

    mock_geocode.side_effect = lambda loc_name: MOCK_DARJEELING if "Darjeeling" in loc_name else MOCK_PARIS
    mock_current.return_value = MOCK_CURRENT
    mock_forecast.return_value = MOCK_FORECAST

    # Step A: Explicit location query -> Darjeeling
    res1 = client.post("/api/chat", json={"message": "What's the weather in Darjeeling tomorrow?", "session_id": test_session})
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["needs_clarification"] is False
    assert d1["location"]["name"] == "Darjeeling"

    # Step B: Follow-up question without location -> reuses Darjeeling from session context!
    res2 = client.post("/api/chat", json={"message": "Should I carry an umbrella?", "session_id": test_session})
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2["needs_clarification"] is False
    assert d2["location"]["name"] == "Darjeeling"
    assert "Darjeeling" in d2["summary"]

    # Step C: Explicit new location -> Paris (overrides previous context)
    res3 = client.post("/api/chat", json={"message": "What's the weather in Paris?", "session_id": test_session})
    assert res3.status_code == 200
    d3 = res3.json()
    assert d3["needs_clarification"] is False
    assert d3["location"]["name"] == "Paris"


@pytest.mark.asyncio
async def test_llm_service_unconfigured_fallback():
    """Test LLM service returns None when AI_API_KEY is unconfigured."""
    llm = LLMService(api_key="")
    assert llm.is_configured is False

    intent = await llm.extract_structured_intent("Will it rain in Kolkata tomorrow?")
    assert intent is None


@pytest.mark.asyncio
async def test_llm_service_ai_explanation_mocked():
    """Test AI explanation with mocked LLM response."""
    llm = LLMService(api_key="mock-test-key")
    from app.schemas.decision import DecisionFactor, DecisionResponse

    mock_decision = DecisionResponse(
        type="umbrella",
        recommendation="recommended",
        confidence="high",
        summary="Carrying an umbrella is recommended for tomorrow evening due to 80% rain probability.",
        factors=[DecisionFactor(metric="precipitation_probability", value="80%", impact="negative")],
    )

    q_info = ExtractedQueryInfo(original_query="Why?", intent="ai_explain", date_context="tomorrow", time_period="evening")

    with patch.object(llm, "_post_chat_completion", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = "An umbrella is recommended for Kolkata tomorrow evening because the forecast indicates an 80% chance of rain."

        res = await llm.generate_ai_explanation("Why?", q_info, "Kolkata", mock_decision)
        assert res is not None
        assert "80% chance of rain" in res


@patch("app.services.query_service.geocoding_service.geocode_location")
@patch("app.services.weather_service.weather_service.get_current_weather")
@patch("app.services.weather_service.weather_service.get_forecast")
def test_chat_why_followup_explanation_flow(mock_forecast, mock_current, mock_geocode):
    """Test decision query followed by 'Why?' receives AI explain grounded response."""
    test_session = "test_session_why_explain"
    SESSION_CONTEXT.pop(test_session, None)

    mock_geocode.return_value = MOCK_DARJEELING
    mock_current.return_value = MOCK_CURRENT
    mock_forecast.return_value = MOCK_FORECAST

    # Step A: Ask decision query
    res1 = client.post("/api/chat", json={"message": "Should I carry an umbrella in Darjeeling tomorrow?", "session_id": test_session})
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["decision"] is not None

    # Step B: Ask "Why?"
    res2 = client.post("/api/chat", json={"message": "Why?", "session_id": test_session})
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2["decision"] is not None
    assert d2["decision"]["type"] == d1["decision"]["type"]
    assert "Explanation" in d2["summary"] or "recommended" in d2["summary"].lower() or "unnecessary" in d2["summary"].lower()


@patch("app.services.query_service.geocoding_service.geocode_location")
@patch("app.services.weather_service.weather_service.get_current_weather")
@patch("app.services.weather_service.weather_service.get_forecast")
def test_phase5_conversational_sequence(mock_forecast, mock_current, mock_geocode):
    """Phase 5: Verify multi-turn conversational follow-up sequence."""
    test_session = "test_phase5_sequence"
    SESSION_CONTEXT.pop(test_session, None)

    mock_geocode.return_value = MOCK_DARJEELING
    mock_current.return_value = MOCK_CURRENT
    mock_forecast.return_value = MOCK_FORECAST

    # 1. Rain query with location and date
    r1 = client.post("/api/chat", json={"message": "Will it rain tomorrow in Darjeeling?", "session_id": test_session})
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["location"]["name"] == "Darjeeling"
    assert d1["query"]["date_context"] == "tomorrow"

    # 2. Follow-up: "What about evening?" -> inherits Darjeeling, tomorrow, evening
    r2 = client.post("/api/chat", json={"message": "What about evening?", "session_id": test_session})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["location"]["name"] == "Darjeeling"
    assert d2["query"]["date_context"] == "tomorrow"
    assert d2["query"]["time_period"] == "evening"

    # 3. Follow-up: "Should I carry an umbrella?" -> inherits Darjeeling, tomorrow, evening
    r3 = client.post("/api/chat", json={"message": "Should I carry an umbrella?", "session_id": test_session})
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["location"]["name"] == "Darjeeling"
    assert d3["decision"] is not None
    assert d3["decision"]["type"] == "umbrella"


@patch("app.services.query_service.geocoding_service.geocode_location")
@patch("app.services.weather_service.weather_service.get_current_weather")
@patch("app.services.weather_service.weather_service.get_forecast")
def test_phase5_location_override_preserves_date(mock_forecast, mock_current, mock_geocode):
    """Phase 5: Verify 'What about Paris?' overrides location while preserving date context."""
    test_session = "test_phase5_override"
    SESSION_CONTEXT.pop(test_session, None)

    mock_geocode.side_effect = lambda loc_name: MOCK_DARJEELING if "Darjeeling" in loc_name else MOCK_PARIS
    mock_current.return_value = MOCK_CURRENT
    mock_forecast.return_value = MOCK_FORECAST

    r1 = client.post("/api/chat", json={"message": "What's the weather tomorrow in Darjeeling?", "session_id": test_session})
    assert r1.json()["location"]["name"] == "Darjeeling"
    assert r1.json()["query"]["date_context"] == "tomorrow"

    r2 = client.post("/api/chat", json={"message": "What about Paris?", "session_id": test_session})
    d2 = r2.json()
    assert d2["location"]["name"] == "Paris"
    assert d2["query"]["date_context"] == "tomorrow"


@patch("app.services.query_service.geocoding_service.geocode_location")
@patch("app.services.weather_service.weather_service.get_current_weather")
@patch("app.services.weather_service.weather_service.get_forecast")
def test_phase5_normal_weather_query_has_no_decision(mock_forecast, mock_current, mock_geocode):
    """Phase 5: Verify general weather query returns decision=None."""
    test_session = "test_phase5_nodecision"
    SESSION_CONTEXT.pop(test_session, None)

    mock_geocode.return_value = MOCK_PARIS
    mock_current.return_value = MOCK_CURRENT
    mock_forecast.return_value = MOCK_FORECAST

    r = client.post("/api/chat", json={"message": "What's the weather in Paris?", "session_id": test_session})
    assert r.status_code == 200
    assert r.json()["decision"] is None


@pytest.mark.asyncio
async def test_llm_service_429_diagnostic_logging_and_no_secrets(caplog):
    """Verify that Groq HTTP 429 triggers diagnostic logging of required rate limit headers without exposing API keys."""
    import logging
    import httpx
    from unittest.mock import MagicMock

    secret_key = "gsk_test_secret_key_abcdef123456"
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    resp_429 = MagicMock(spec=httpx.Response)
    resp_429.status_code = 429
    resp_429.headers = {
        "retry-after": "5",
        "x-ratelimit-limit-requests": "14400",
        "x-ratelimit-remaining-requests": "0",
        "x-ratelimit-reset-requests": "1.2s",
        "x-ratelimit-limit-tokens": "6000",
        "x-ratelimit-remaining-tokens": "0",
        "x-ratelimit-reset-tokens": "60s",
        "Authorization": f"Bearer {secret_key}",
    }
    resp_429.raise_for_status.side_effect = httpx.HTTPStatusError("429 Too Many Requests", request=None, response=resp_429)
    mock_client.post.return_value = resp_429

    service = LLMService(api_key=secret_key, client=mock_client)

    with caplog.at_level(logging.WARNING):
        result = await service.extract_structured_intent("Will it rain tomorrow in Kolkata?")

    assert result is None  # Deterministic fallback triggers

    # Check diagnostic log
    log_text = " ".join(record.message for record in caplog.records)
    assert "Groq API HTTP 429 rate limit response received" in log_text
    assert "x-ratelimit-remaining-requests" in log_text
    assert "x-ratelimit-reset-tokens" in log_text

    # CRITICAL: Secret API key and authorization tokens must NEVER be logged
    assert secret_key not in log_text
    assert "gsk_" not in log_text


