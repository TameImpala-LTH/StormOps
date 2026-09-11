"""Unit tests for user conversation history, message persistence, and strict data isolation."""

import app.core.compat  # noqa: F401
import pytest
from unittest.mock import patch

from app.models.conversation import Conversation
from app.models.message import Message


def test_authenticated_chat_persists_conversation_and_messages(client, db_session):
    """Verify authenticated /api/chat persists conversation and messages."""
    # Register user
    reg = client.post(
        "/api/auth/register",
        json={"email": "history_user@example.com", "password": "password123", "display_name": "History User"},
    )
    token = reg.json()["access_token"]
    user_id = reg.json()["user"]["id"]

    # Send chat query with auth token
    res = client.post(
        "/api/chat",
        json={"message": "What's the weather in Kolkata today?", "session_id": "test_sess_1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "summary" in data

    # Verify conversation was persisted in DB
    convs = db_session.query(Conversation).filter(Conversation.user_id == user_id).all()
    assert len(convs) == 1
    assert "Kolkata" in convs[0].title or "weather" in convs[0].title
    assert convs[0].location_name == "Kolkata"

    # Verify messages were persisted (1 user + 1 assistant)
    msgs = db_session.query(Message).filter(Message.conversation_id == convs[0].id).all()
    assert len(msgs) == 2
    assert msgs[0].role == "user"
    assert msgs[0].content == "What's the weather in Kolkata today?"
    assert msgs[1].role == "assistant"
    assert msgs[1].content == data["summary"]


def test_history_strict_user_data_isolation(client):
    """Verify User A cannot list, view, or delete User B's conversations."""
    # Register User A
    reg_a = client.post(
        "/api/auth/register",
        json={"email": "user_a@example.com", "password": "password123", "display_name": "User A"},
    )
    token_a = reg_a.json()["access_token"]

    # Register User B
    reg_b = client.post(
        "/api/auth/register",
        json={"email": "user_b@example.com", "password": "password123", "display_name": "User B"},
    )
    token_b = reg_b.json()["access_token"]

    # User A creates a conversation
    chat_a = client.post(
        "/api/chat",
        json={"message": "Weather in Kolkata today?"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert chat_a.status_code == 200

    # User A lists history -> sees 1 conversation
    list_a = client.get("/api/history", headers={"Authorization": f"Bearer {token_a}"})
    assert list_a.status_code == 200
    items_a = list_a.json()
    assert len(items_a) == 1
    conv_a_id = items_a[0]["id"]

    # User B lists history -> sees 0 conversations (complete data isolation)
    list_b = client.get("/api/history", headers={"Authorization": f"Bearer {token_b}"})
    assert list_b.status_code == 200
    assert len(list_b.json()) == 0

    # User B attempts to access User A's conversation detail -> returns 404
    get_b = client.get(f"/api/history/{conv_a_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert get_b.status_code == 404

    # User B attempts to delete User A's conversation -> returns 404
    del_b = client.delete(f"/api/history/{conv_a_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert del_b.status_code == 404

    # User A can successfully retrieve detail
    get_a = client.get(f"/api/history/{conv_a_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert get_a.status_code == 200
    assert len(get_a.json()["messages"]) == 2

    # User A deletes their own conversation -> succeeds with 204
    del_a = client.delete(f"/api/history/{conv_a_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert del_a.status_code == 204

    # Confirm history is now empty
    list_a_after = client.get("/api/history", headers={"Authorization": f"Bearer {token_a}"})
    assert len(list_a_after.json()) == 0


def test_anonymous_chat_does_not_persist_db_records(client, db_session):
    """Verify anonymous queries do not create persistent DB records and continue working seamlessly."""
    initial_conv_count = db_session.query(Conversation).count()

    res = client.post(
        "/api/chat",
        json={"message": "What is the weather in Paris?"},
    )
    assert res.status_code == 200
    assert "Paris" in res.json()["summary"]

    after_conv_count = db_session.query(Conversation).count()
    assert after_conv_count == initial_conv_count


def test_conversation_continuation_and_session_preseed(client, db_session):
    """Verify that continuing an authenticated conversation preserves location context and appends messages."""
    # 1. Register user
    reg = client.post(
        "/api/auth/register",
        json={"email": "continuation_user@example.com", "password": "password123", "display_name": "Continuation User"},
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]

    # 2. Turn 1: Ask weather in Mumbai
    chat1 = client.post(
        "/api/chat",
        json={"message": "What is the weather in Mumbai?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert chat1.status_code == 200
    conv_id = chat1.json()["session_id"]
    assert conv_id is not None
    assert "Mumbai" in chat1.json()["location"]["name"]

    # 3. Simulate server restart / browser reload by clearing query_service.SESSION_CONTEXT
    from app.services.query_service import SESSION_CONTEXT
    SESSION_CONTEXT.clear()
    assert conv_id not in SESSION_CONTEXT

    # 4. Turn 2: Follow-up question without explicit location
    chat2 = client.post(
        "/api/chat",
        json={"message": "Will it rain tomorrow?", "session_id": conv_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert chat2.status_code == 200
    res2 = chat2.json()
    assert res2["needs_clarification"] is False
    assert res2["location"] is not None
    assert "Mumbai" in res2["location"]["name"]

    # 5. Check conversation detail: should now have 4 messages
    detail = client.get(f"/api/history/{conv_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    assert len(messages) == 4
    assert messages[0]["content"] == "What is the weather in Mumbai?"
    assert messages[2]["content"] == "Will it rain tomorrow?"

    # 6. Check /api/history list preview reflects last_query and last_answer
    hist = client.get("/api/history", headers={"Authorization": f"Bearer {token}"})
    assert hist.status_code == 200
    hist_items = hist.json()
    assert len(hist_items) == 1
    assert hist_items[0]["last_query"] == "Will it rain tomorrow?"
    assert hist_items[0]["location_name"] == "Mumbai"


def test_history_pagination_bounds(client, db_session):
    """Verify limit and offset query parameters for /api/history."""
    reg = client.post(
        "/api/auth/register",
        json={"email": "page_user@example.com", "password": "password123", "display_name": "Page User"},
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create 3 conversations
    for loc in ["Delhi", "Kolkata", "Mumbai"]:
        res = client.post("/api/chat", json={"message": f"Weather in {loc}?"}, headers=headers)
        assert res.status_code == 200

    # Total 3 conversations
    all_res = client.get("/api/history", headers=headers)
    assert all_res.status_code == 200
    assert len(all_res.json()) == 3

    # Limit 2
    page1 = client.get("/api/history?limit=2&offset=0", headers=headers)
    assert page1.status_code == 200
    assert len(page1.json()) == 2

    # Offset 2
    page2 = client.get("/api/history?limit=2&offset=2", headers=headers)
    assert page2.status_code == 200
    assert len(page2.json()) == 1


def test_history_not_found_or_invalid_id(client):
    """Verify 404 for non-existent or malformed conversation IDs."""
    reg = client.post(
        "/api/auth/register",
        json={"email": "notfound_user@example.com", "password": "password123", "display_name": "NF User"},
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Non-existent ID
    res = client.get("/api/history/non-existent-uuid-1234", headers=headers)
    assert res.status_code == 404

    # Delete non-existent ID
    res_del = client.delete("/api/history/non-existent-uuid-1234", headers=headers)
    assert res_del.status_code == 404

