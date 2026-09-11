"""Unit tests for Phase 14 Personal Weather Timeline and Environmental Outlook API."""

import app.core.compat  # noqa: F401
import pytest
from app.models.conversation import Conversation
from app.models.message import Message


def test_timeline_last_query_and_last_answer(client, db_session):
    """Verify list_user_history populates last_query and last_answer for timeline presentation."""
    # Register test user
    reg = client.post(
        "/api/auth/register",
        json={"email": "timeline_user@example.com", "password": "password123", "display_name": "Timeline User"},
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]

    # Send a query
    chat_res = client.post(
        "/api/chat",
        json={"message": "Will it rain in Kolkata today?", "session_id": "timeline_sess_1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert chat_res.status_code == 200
    answer_text = chat_res.json()["summary"]

    # Call /api/history (Personal Weather Timeline)
    hist_res = client.get("/api/history", headers={"Authorization": f"Bearer {token}"})
    assert hist_res.status_code == 200
    items = hist_res.json()
    assert len(items) == 1

    item = items[0]
    assert item["last_query"] == "Will it rain in Kolkata today?"
    assert item["last_answer"] == answer_text
    assert item["location_name"] == "Kolkata"
    assert "updated_at" in item


def test_environmental_events_endpoint(client):
    """Verify /api/weather/events returns deterministic verified catalogue events."""
    # Test with Kolkata (should match Durga Puja and Chhath Puja)
    res_kolkata = client.get("/api/weather/events?location=Kolkata")
    assert res_kolkata.status_code == 200
    kolkata_events = res_kolkata.json()
    assert len(kolkata_events) >= 1
    event_ids = [e["id"] for e in kolkata_events]
    assert "kolkata-durga-puja-2026" in event_ids or "kolkata-chhath-puja-2026" in event_ids

    # Test with empty or unknown location
    res_empty = client.get("/api/weather/events?location=")
    assert res_empty.status_code == 200
    assert res_empty.json() == []

    # Test with unknown city that has no verified regional catalogue events
    res_unknown = client.get("/api/weather/events?location=Anchorage")
    assert res_unknown.status_code == 200
    assert res_unknown.json() == []
