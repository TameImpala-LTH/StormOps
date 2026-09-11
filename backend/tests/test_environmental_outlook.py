"""Unit tests for Phase 14C: Environmental Outlook.

Tests coverage:
1. authenticated user with one saved location
2. authenticated user with multiple saved locations
3. no saved locations
4. no matching environmental events
5. active event
6. upcoming event
7. multiple events sorted correctly (active -> upcoming by days_until -> post_event)
8. duplicate event/location handling
9. User A cannot receive User B's saved-location events
10. anonymous request behavior (401 Unauthorized)
11. existing 60-day horizon remains respected
12. EventService remains the single source of truth
"""

from datetime import date
import app.core.compat  # noqa: F401
from unittest.mock import patch
import pytest

from app.schemas.event import EnvironmentalEvent, EnvironmentalPressureItem, EventOccurrence
from app.services.event_service import EventService, event_service


def _register_and_get_auth(client, email="outlook_user@example.com"):
    """Helper to create user and return authorization header."""
    res = client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123", "display_name": "Outlook User"},
    )
    assert res.status_code == 201
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_1_authenticated_user_one_saved_location(client):
    """Test 1: Authenticated user with one saved location receives matching event."""
    headers = _register_and_get_auth(client, "user_kolkata@example.com")

    # Save Kolkata
    client.post(
        "/api/locations",
        json={"name": "Kolkata", "latitude": 22.5726, "longitude": 88.3639, "country": "India"},
        headers=headers,
    )

    # Reference date within 60 days of Durga Puja 2026 (starts Oct 16)
    ref_date = date(2026, 9, 15)
    with patch("app.services.event_service.date") as mock_date:
        mock_date.today.return_value = ref_date
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

        res = client.get("/api/environmental/outlook", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total_events"] >= 1
        assert "Kolkata" in data["locations_evaluated"]
        titles = [item["event_title"] for item in data["items"]]
        assert "Durga Puja Festival" in titles

        # Verify non-predictive evidence note
        item = next(i for i in data["items"] if i["event_title"] == "Durga Puja Festival")
        assert item["location_name"] == "Kolkata"
        assert item["evidence_note"] == "Historically associated with increased local environmental pressure."
        assert len(item["environmental_pressures"]) > 0


def test_2_authenticated_user_multiple_saved_locations(client):
    """Test 2: Authenticated user with multiple saved locations (Kolkata + Mumbai)."""
    headers = _register_and_get_auth(client, "user_multi@example.com")

    client.post(
        "/api/locations",
        json={"name": "Kolkata", "latitude": 22.5726, "longitude": 88.3639, "country": "India"},
        headers=headers,
    )
    client.post(
        "/api/locations",
        json={"name": "Mumbai", "latitude": 19.0760, "longitude": 72.8777, "country": "India"},
        headers=headers,
    )

    ref_date = date(2026, 9, 10)
    with patch("app.services.event_service.date") as mock_date:
        mock_date.today.return_value = ref_date
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

        res = client.get("/api/environmental/outlook", headers=headers)
        assert res.status_code == 200
        data = res.json()
        titles = [i["event_title"] for i in data["items"]]
        assert "Ganesh Chaturthi Festival" in titles
        assert "Durga Puja Festival" in titles


def test_3_no_saved_locations(client):
    """Test 3: Authenticated user with zero saved locations returns empty list cleanly."""
    headers = _register_and_get_auth(client, "user_empty@example.com")

    res = client.get("/api/environmental/outlook", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_events"] == 0
    assert data["items"] == []
    assert data["locations_evaluated"] == []


def test_4_no_matching_environmental_events(client):
    """Test 4: Saved locations with no matching environmental events (e.g. Paris, Tokyo)."""
    headers = _register_and_get_auth(client, "user_foreign@example.com")

    client.post(
        "/api/locations",
        json={"name": "Paris", "latitude": 48.8566, "longitude": 2.3522, "country": "France"},
        headers=headers,
    )

    res = client.get("/api/environmental/outlook", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_events"] == 0
    assert data["items"] == []
    assert "Paris" in data["locations_evaluated"]


def test_5_active_event_status_and_ordering(client):
    """Test 5: Active event status is correctly assigned and prioritized."""
    headers = _register_and_get_auth(client, "user_active@example.com")

    client.post(
        "/api/locations",
        json={"name": "Mumbai", "latitude": 19.0760, "longitude": 72.8777, "country": "India"},
        headers=headers,
    )

    # Ganesh Chaturthi 2026 runs Sep 14 to Sep 24. Sep 18 is active.
    ref_date = date(2026, 9, 18)
    with patch("app.services.event_service.date") as mock_date:
        mock_date.today.return_value = ref_date
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

        res = client.get("/api/environmental/outlook", headers=headers)
        assert res.status_code == 200
        data = res.json()
        item = next(i for i in data["items"] if i["event_title"] == "Ganesh Chaturthi Festival")
        assert item["status"] == "active"
        assert item["days_until"] == 0


def test_6_upcoming_event_days_until(client):
    """Test 6: Upcoming event has positive days_until calculation."""
    headers = _register_and_get_auth(client, "user_upcoming@example.com")

    client.post(
        "/api/locations",
        json={"name": "Kolkata", "latitude": 22.5726, "longitude": 88.3639, "country": "India"},
        headers=headers,
    )

    # Durga Puja starts Oct 16. On Sep 16, days_until should be 30.
    ref_date = date(2026, 9, 16)
    with patch("app.services.event_service.date") as mock_date:
        mock_date.today.return_value = ref_date
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

        res = client.get("/api/environmental/outlook", headers=headers)
        assert res.status_code == 200
        data = res.json()
        item = next(i for i in data["items"] if i["event_title"] == "Durga Puja Festival")
        assert item["status"] == "upcoming"
        assert item["days_until"] == 30


def test_7_multiple_events_sorted_correctly(client):
    """Test 7: Multiple events are sorted active first, then soonest upcoming."""
    headers = _register_and_get_auth(client, "user_sorted@example.com")

    client.post(
        "/api/locations",
        json={"name": "Mumbai", "latitude": 19.0760, "longitude": 72.8777, "country": "India"},
        headers=headers,
    )
    client.post(
        "/api/locations",
        json={"name": "Kolkata", "latitude": 22.5726, "longitude": 88.3639, "country": "India"},
        headers=headers,
    )

    # On Sep 18, 2026:
    # Mumbai Ganesh Chaturthi (Sep 14 - Sep 24) is ACTIVE
    # Kolkata Durga Puja (starts Oct 16) is UPCOMING (28 days)
    ref_date = date(2026, 9, 18)
    with patch("app.services.event_service.date") as mock_date:
        mock_date.today.return_value = ref_date
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

        res = client.get("/api/environmental/outlook", headers=headers)
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) >= 2
        # First item must be active
        assert items[0]["status"] == "active"
        # Second item must be upcoming
        assert items[1]["status"] == "upcoming"


def test_8_duplicate_event_and_location_handling(client):
    """Test 8: Current location duplicate with saved location is not evaluated twice."""
    headers = _register_and_get_auth(client, "user_dup@example.com")

    client.post(
        "/api/locations",
        json={"name": "Kolkata", "latitude": 22.5726, "longitude": 88.3639, "country": "India"},
        headers=headers,
    )

    ref_date = date(2026, 9, 16)
    with patch("app.services.event_service.date") as mock_date:
        mock_date.today.return_value = ref_date
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

        # Pass current_location="Kolkata" when Kolkata is already in saved locations
        res = client.get("/api/environmental/outlook?current_location=Kolkata", headers=headers)
        assert res.status_code == 200
        data = res.json()
        kolkata_durga = [i for i in data["items"] if i["event_title"] == "Durga Puja Festival"]
        # Must only appear once
        assert len(kolkata_durga) == 1


def test_9_user_a_cannot_receive_user_b_events(client):
    """Test 9: Strict ownership isolation between User A and User B."""
    headers_a = _register_and_get_auth(client, "user_a@example.com")
    headers_b = _register_and_get_auth(client, "user_b@example.com")

    # User A saves Kolkata
    client.post(
        "/api/locations",
        json={"name": "Kolkata", "latitude": 22.5726, "longitude": 88.3639, "country": "India"},
        headers=headers_a,
    )

    # User B saves Mumbai
    client.post(
        "/api/locations",
        json={"name": "Mumbai", "latitude": 19.0760, "longitude": 72.8777, "country": "India"},
        headers=headers_b,
    )

    ref_date = date(2026, 9, 10)
    with patch("app.services.event_service.date") as mock_date:
        mock_date.today.return_value = ref_date
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

        res_a = client.get("/api/environmental/outlook", headers=headers_a)
        res_b = client.get("/api/environmental/outlook", headers=headers_b)

        titles_a = [i["event_title"] for i in res_a.json()["items"]]
        titles_b = [i["event_title"] for i in res_b.json()["items"]]

        # User A must only have Kolkata events
        assert "Durga Puja Festival" in titles_a
        assert "Ganesh Chaturthi Festival" not in titles_a
        assert "Mumbai" not in res_a.json()["locations_evaluated"]

        # User B must only have Mumbai events
        assert "Ganesh Chaturthi Festival" in titles_b
        assert "Durga Puja Festival" not in titles_b
        assert "Kolkata" not in res_b.json()["locations_evaluated"]


def test_10_anonymous_request_behavior(client):
    """Test 10: Anonymous request without Authorization header returns 401."""
    res = client.get("/api/environmental/outlook")
    assert res.status_code == 401
    assert "detail" in res.json()


def test_11_sixty_day_horizon_respected(client):
    """Test 11: Events further out than 60 days are not included in outlook."""
    headers = _register_and_get_auth(client, "user_horizon@example.com")

    client.post(
        "/api/locations",
        json={"name": "Kolkata", "latitude": 22.5726, "longitude": 88.3639, "country": "India"},
        headers=headers,
    )

    # On July 1, 2026: Durga Puja (Oct 16) is ~107 days away (>60 days)
    ref_date = date(2026, 7, 1)
    with patch("app.services.event_service.date") as mock_date:
        mock_date.today.return_value = ref_date
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

        res = client.get("/api/environmental/outlook", headers=headers)
        assert res.status_code == 200
        assert res.json()["total_events"] == 0
        assert res.json()["items"] == []


def test_12_event_service_single_source_of_truth(client):
    """Test 12: EventService remains the direct and only provider of event data."""
    headers = _register_and_get_auth(client, "user_single_source@example.com")

    custom_event = EnvironmentalEvent(
        id="test-civic-marathon-2026",
        title="City Marathon",
        category="sports",
        geographic_scope=["Bengaluru"],
        occurrences=[
            EventOccurrence(
                year=2026,
                start_date="2026-09-20",
                end_date="2026-09-20",
                post_event_days=1,
            )
        ],
        environmental_pressures=[
            EnvironmentalPressureItem(type="traffic", level="high", evidence_type="historical_pattern")
        ],
        advisory_summary="City marathon causes traffic closures.",
        key_recommendations=["Use alternate routes"],
        source_metadata="Test Marathon Registry",
    )

    client.post(
        "/api/locations",
        json={"name": "Bengaluru", "latitude": 12.9716, "longitude": 77.5946, "country": "India"},
        headers=headers,
    )

    # Patch catalogue directly in EventService instance
    with patch.object(event_service, "catalogue", [custom_event]):
        ref_date = date(2026, 9, 15)
        with patch("app.services.event_service.date") as mock_date:
            mock_date.today.return_value = ref_date
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

            res = client.get("/api/environmental/outlook", headers=headers)
            assert res.status_code == 200
            data = res.json()
            assert data["total_events"] == 1
            assert data["items"][0]["event_title"] == "City Marathon"
