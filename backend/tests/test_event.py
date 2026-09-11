"""Comprehensive unit and integration tests for Phase 10A Event-Based Environmental Awareness layer."""

from datetime import date
import app.core.compat  # noqa: F401
from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.schemas.event import EnvironmentalEvent
from app.schemas.query import GeocodedLocationSchema
from app.schemas.weather import (
    CurrentWeather,
    CurrentWeatherResponse,
    ForecastResponse,
    HourlyForecast,
    LocationCoordinates,
)
from app.services.event_service import EventService, event_service
from app.services.query_service import SESSION_CONTEXT

client = TestClient(app)

MOCK_KOLKATA = GeocodedLocationSchema(
    name="Kolkata", country="India", admin1="West Bengal", latitude=22.5726, longitude=88.3639, timezone="Asia/Kolkata"
)
MOCK_MUMBAI = GeocodedLocationSchema(
    name="Mumbai", country="India", admin1="Maharashtra", latitude=19.0760, longitude=72.8777, timezone="Asia/Kolkata"
)
MOCK_DELHI = GeocodedLocationSchema(
    name="Delhi", country="India", admin1="Delhi", latitude=28.6139, longitude=77.2090, timezone="Asia/Kolkata"
)
MOCK_PARIS = GeocodedLocationSchema(
    name="Paris", country="France", admin1="Ile-de-France", latitude=48.8534, longitude=2.3488, timezone="Europe/Paris"
)

MOCK_CURRENT = CurrentWeatherResponse(
    location=LocationCoordinates(latitude=22.5726, longitude=88.3639, name="Kolkata", timezone="Asia/Kolkata"),
    current=CurrentWeather(
        temperature=28.0, feels_like=30.0, condition="Clear", weather_code=0, humidity=65, wind_speed=10.0, precipitation=0.0, precipitation_probability=10, time="2026-09-07T12:00"
    ),
    source="open-meteo",
    timestamp="2026-09-07T12:00:00Z",
)

MOCK_FORECAST = ForecastResponse(
    location=LocationCoordinates(latitude=22.5726, longitude=88.3639, name="Kolkata", timezone="Asia/Kolkata"),
    hourly=[
        HourlyForecast(
            time="2026-09-07T12:00", temperature=28.0, condition="Clear", weather_code=0, precipitation_probability=10, precipitation=0.0, wind_speed=10.0
        )
    ],
    source="open-meteo",
    timestamp="2026-09-07T12:00:00Z",
)


def test_1_kolkata_durga_puja_matching():
    """Test 1: Kolkata matches 2026 Durga Puja event."""
    events = event_service.get_location_events("Kolkata", target_date=date(2026, 9, 7))
    titles = [e.title for e in events]
    assert "Durga Puja Festival" in titles


def test_2_mumbai_ganesh_chaturthi_matching():
    """Test 2: Mumbai matches 2026 Ganesh Chaturthi event."""
    events = event_service.get_location_events("Mumbai", target_date=date(2026, 9, 7))
    titles = [e.title for e in events]
    assert "Ganesh Chaturthi Festival" in titles


def test_3_mumbai_diwali_matching():
    """Test 3: Mumbai matches 2026 Diwali event when queried near Diwali date."""
    events = event_service.get_location_events("Mumbai", target_date=date(2026, 11, 1))
    titles = [e.title for e in events]
    assert "Diwali Celebrations" in titles


def test_4_delhi_diwali_matching():
    """Test 4: Delhi matches 2026 Diwali event."""
    events = event_service.get_location_events("Delhi", target_date=date(2026, 11, 1))
    titles = [e.title for e in events]
    assert "Diwali Celebrations" in titles


def test_5_unrelated_city_no_events():
    """Test 5: Unrelated city (e.g. Paris) returns empty events list."""
    events = event_service.get_location_events("Paris", target_date=date(2026, 9, 7))
    assert len(events) == 0


def test_6_upcoming_event_status():
    """Test 6: Upcoming event status and days_until calculation."""
    # Durga Puja starts 2026-10-16. On 2026-09-16, days_until should be 30 and status upcoming.
    events = event_service.get_location_events("Kolkata", target_date=date(2026, 9, 16))
    assert len(events) > 0
    dp = next(e for e in events if e.title == "Durga Puja Festival")
    assert dp.status == "upcoming"
    assert dp.days_until == 30


def test_7_active_event_status():
    """Test 7: Active event status when target_date is during festival."""
    # Durga Puja active 2026-10-16 to 2026-10-21.
    events = event_service.get_location_events("Kolkata", target_date=date(2026, 10, 18))
    dp = next(e for e in events if e.title == "Durga Puja Festival")
    assert dp.status == "active"
    assert dp.days_until == 0


def test_8_post_event_status():
    """Test 8: Post-event status within post_event_days window."""
    # Durga Puja ends 2026-10-21, post_event_days=3 (up to 2026-10-24).
    events = event_service.get_location_events("Kolkata", target_date=date(2026, 10, 23))
    dp = next(e for e in events if e.title == "Durga Puja Festival")
    assert dp.status == "post_event"
    assert dp.days_until == 0


def test_9_expired_event():
    """Test 9: Expired event outside visibility window returns no active event."""
    # On 2026-01-01, 2026-10-16 Durga Puja is outside 60-day visibility window.
    events = event_service.get_location_events("Kolkata", target_date=date(2026, 1, 1))
    assert len(events) == 0


def test_10_multiple_applicable_events():
    """Test 10: Multiple applicable events for Mumbai when date window overlaps both."""
    # Ganesh Chaturthi ends 2026-09-24 (+3 days post = 09-27). Visibility for Diwali (starts 11-08) starts 09-09.
    # On 2026-09-20, Ganesh Chaturthi is active, and Diwali is upcoming within 60 days!
    events = event_service.get_location_events("Mumbai", target_date=date(2026, 9, 20))
    titles = [e.title for e in events]
    assert "Ganesh Chaturthi Festival" in titles
    assert "Diwali Celebrations" in titles


def test_11_empty_event_list():
    """Test 11: Empty event list returned for empty or invalid location name."""
    assert event_service.get_location_events("") == []


@patch("app.services.query_service.geocoding_service.reverse_geocode")
@patch("app.services.weather_service.weather_service.get_current_weather")
@patch("app.services.weather_service.weather_service.get_forecast")
def test_12_current_location_resolved_city_event_lookup(mock_forecast, mock_current, mock_reverse_geo):
    """Test 12: Device geolocation resolving to Kolkata triggers event lookup."""
    test_session = "test_sess_geo_events"
    SESSION_CONTEXT.pop(test_session, None)

    mock_reverse_geo.return_value = MOCK_KOLKATA
    mock_current.return_value = MOCK_CURRENT
    mock_forecast.return_value = MOCK_FORECAST

    payload = {
        "message": "What's the weather at my location?",
        "session_id": test_session,
        "location": {"latitude": 22.5726, "longitude": 88.3639}
    }

    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["environmental_events"] is not None
    assert len(data["environmental_events"]) > 0
    titles = [e["title"] for e in data["environmental_events"]]
    assert "Durga Puja Festival" in titles


def test_13_event_facts_separate_from_advisories():
    """Test 13: Event facts (occurrences/dates) remain distinct from environmental pressure advisories."""
    events = event_service.get_location_events("Kolkata", target_date=date(2026, 9, 7))
    dp = next(e for e in events if e.title == "Durga Puja Festival")

    # Fact check: dates
    assert dp.occurrences[0].start_date == "2026-10-16"
    assert dp.occurrences[0].end_date == "2026-10-21"

    # Advisory check: environmental pressures & recommendations
    pressures = [p.type for p in dp.environmental_pressures]
    assert "traffic" in pressures
    assert "noise_pollution" in pressures
    assert "Verified 2026" in dp.source_metadata


# ─────────────────────────────────────────────────────────────────────────────
# Phase 10B Tests (14–20)
# ─────────────────────────────────────────────────────────────────────────────

def test_14_event_ordering_active_first():
    """Test 14: Active event is returned before upcoming events in sort order.
    On 2026-10-18, Durga Puja is active. Chhath Puja (Nov 13) is upcoming within 60 days.
    The first element in the returned list must be the active Durga Puja."""
    events = event_service.get_location_events("Kolkata", target_date=date(2026, 10, 18))
    assert len(events) >= 1
    assert events[0].status == "active"
    assert events[0].title == "Durga Puja Festival"
    # All upcoming events must follow the active event
    for e in events[1:]:
        assert e.status in ("upcoming", "post_event")


def test_15_event_ordering_upcoming_soonest_first():
    """Test 15: On Sep 9 both Mumbai events enter the 60-day window.
    Ganesh Chaturthi (Sep 14, 5 days) must appear before Diwali (Nov 8, 60 days).
    Sep 7 is intentionally NOT used — Diwali (62 days) is outside the window on Sep 7."""
    events = event_service.get_location_events("Mumbai", target_date=date(2026, 9, 9))
    titles = [e.title for e in events]
    assert "Ganesh Chaturthi Festival" in titles
    assert "Diwali Celebrations" in titles

    gc_idx = titles.index("Ganesh Chaturthi Festival")
    diwali_idx = titles.index("Diwali Celebrations")
    assert gc_idx < diwali_idx, "Ganesh Chaturthi (soonest) must appear before Diwali in sort order"

    assert events[gc_idx].days_until == 5
    assert events[diwali_idx].days_until == 60


def test_16_date_today_fallback():
    """Test 16: get_location_events() must use date.today() as the default ref_date,
    NOT the previously hardcoded date(2026, 9, 7).

    This test is non-tautological: it patches date.today() to date(2026, 11, 1),
    a date different from today (Sep 7) and different from the hardcoded fallback.

    With the fix: days_until for Delhi Diwali (Nov 8) = 7.
    With the bug (hardcoded 2026-09-07): days_until = 62.
    The assertion on days_until == 7 is a definitive distinguisher."""
    from unittest.mock import patch, MagicMock
    import app.services.event_service as es_module

    mock_date_class = MagicMock(wraps=date)
    mock_date_class.today.return_value = date(2026, 11, 1)

    with patch.object(es_module, "date", mock_date_class):
        svc = es_module.EventService()
        events = svc.get_location_events("Delhi")  # no target_date — must use mocked date.today()

    diwali_events = [e for e in events if e.title == "Diwali Celebrations"]
    assert len(diwali_events) > 0, "Delhi Diwali must be visible on mocked date 2026-11-01 (7 days ahead)"
    diwali = diwali_events[0]
    assert diwali.status == "upcoming"
    assert diwali.days_until == 7, (
        f"Expected days_until=7 (date.today() mocked to 2026-11-01), "
        f"got {diwali.days_until}. Value of 62 means hardcoded 2026-09-07 bug is still present."
    )


def test_17_60_day_horizon_visible_boundary():
    """Test 17: An event starting exactly 60 days from ref_date is visible (boundary inclusive).
    Diwali starts 2026-11-08. ref_date=2026-09-09 → exactly 60 days → must be visible."""
    events = event_service.get_location_events("Mumbai", target_date=date(2026, 9, 9))
    titles = [e.title for e in events]
    assert "Diwali Celebrations" in titles, (
        "Diwali must be visible exactly at the 60-day boundary (Sep 9 to Nov 8 = 60 days)"
    )
    diwali = next(e for e in events if e.title == "Diwali Celebrations")
    assert diwali.status == "upcoming"
    assert diwali.days_until == 60


def test_18_60_day_horizon_invisible_boundary():
    """Test 18: An event starting 62 days from ref_date is NOT visible (outside window).
    On Sep 7, Diwali (Nov 8) is 62 days away — must NOT appear in Mumbai results.
    Ganesh Chaturthi (7 days, within window) must still be present."""
    events = event_service.get_location_events("Mumbai", target_date=date(2026, 9, 7))
    titles = [e.title for e in events]
    assert "Diwali Celebrations" not in titles, (
        "Diwali must NOT be visible on Sep 7 — it is 62 days away, outside the 60-day window"
    )
    assert "Ganesh Chaturthi Festival" in titles, (
        "Ganesh Chaturthi (7 days away) must still be visible on Sep 7"
    )


def test_19_post_event_sort_after_upcoming():
    """Test 19: Post-event entries appear after upcoming entries in sort order.
    On 2026-10-23, Durga Puja is post_event (ended Oct 21, within 3-day window).
    Chhath Puja (Nov 13, 21 days away) is upcoming. Upcoming must precede post_event."""
    events = event_service.get_location_events("Kolkata", target_date=date(2026, 10, 23))
    statuses = [e.status for e in events]
    assert "post_event" in statuses, "Durga Puja should be in post_event status on Oct 23"
    assert "upcoming" in statuses, "Chhath Puja should be upcoming on Oct 23"

    upcoming_indices = [i for i, e in enumerate(events) if e.status == "upcoming"]
    post_indices = [i for i, e in enumerate(events) if e.status == "post_event"]
    assert min(upcoming_indices) < min(post_indices), (
        "All upcoming events must appear before post_event events in sort order"
    )


def test_20_existing_weather_queries_unaffected():
    """Test 20: Weather queries for a city with no catalogue events (London) return
    empty environmental_events, and the WeatherGPT summary never mentions festival names."""
    from unittest.mock import patch
    from app.schemas.weather import (
        CurrentWeather, CurrentWeatherResponse, ForecastResponse,
        HourlyForecast, LocationCoordinates,
    )
    from app.schemas.query import GeocodedLocationSchema
    from app.services.query_service import SESSION_CONTEXT

    test_session = "test_sess_p10b_london"
    SESSION_CONTEXT.pop(test_session, None)

    mock_london = GeocodedLocationSchema(
        name="London", country="United Kingdom", admin1="England",
        latitude=51.5074, longitude=-0.1278, timezone="Europe/London",
    )
    mock_current = CurrentWeatherResponse(
        location=LocationCoordinates(latitude=51.5074, longitude=-0.1278, name="London", timezone="Europe/London"),
        current=CurrentWeather(
            temperature=15.0, feels_like=13.0, condition="Cloudy", weather_code=3,
            humidity=70, wind_speed=12.0, precipitation=0.0, precipitation_probability=20,
            time="2026-09-07T12:00",
        ),
        source="open-meteo",
        timestamp="2026-09-07T12:00:00Z",
    )
    mock_forecast = ForecastResponse(
        location=LocationCoordinates(latitude=51.5074, longitude=-0.1278, name="London", timezone="Europe/London"),
        hourly=[
            HourlyForecast(
                time="2026-09-07T12:00", temperature=15.0, condition="Cloudy", weather_code=3,
                precipitation_probability=20, precipitation=0.0, wind_speed=12.0,
            )
        ],
        source="open-meteo",
        timestamp="2026-09-07T12:00:00Z",
    )

    with patch("app.services.query_service.geocoding_service.geocode_location", return_value=mock_london), \
         patch("app.services.weather_service.weather_service.get_current_weather", return_value=mock_current), \
         patch("app.services.weather_service.weather_service.get_forecast", return_value=mock_forecast):
        response = client.post("/api/chat", json={
            "message": "What's the weather in London?",
            "session_id": test_session,
        })

    assert response.status_code == 200
    data = response.json()
    env_events = data.get("environmental_events")
    assert not env_events, f"London must return empty environmental_events, got: {env_events}"

    summary = data.get("summary", "").lower()
    for keyword in ["durga", "ganesh", "diwali", "chhath", "navratri"]:
        assert keyword not in summary, (
            f"WeatherGPT summary must not mention festival '{keyword}', found in: {summary!r}"
        )
