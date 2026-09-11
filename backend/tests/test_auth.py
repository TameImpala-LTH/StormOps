"""Unit tests for user registration, login, JWT token auth, and profile retrieval."""

import app.core.compat  # noqa: F401
import pytest


def test_register_success(client):
    """Verify standard user registration creates account and returns JWT token and user info."""
    res = client.post(
        "/api/auth/register",
        json={
            "email": "user1@example.com",
            "password": "strongpassword123",
            "display_name": "Test User",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "user1@example.com"
    assert data["user"]["display_name"] == "Test User"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


def test_register_duplicate_email(client):
    """Verify duplicate email registration is rejected with 400."""
    payload = {
        "email": "duplicate@example.com",
        "password": "password123",
        "display_name": "First User",
    }
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


def test_login_success_and_invalid_credentials(client):
    """Verify login with correct vs wrong credentials."""
    client.post(
        "/api/auth/register",
        json={
            "email": "login_test@example.com",
            "password": "correctpassword",
            "display_name": "Login User",
        },
    )

    # Correct credentials
    res_ok = client.post(
        "/api/auth/login",
        json={"email": "login_test@example.com", "password": "correctpassword"},
    )
    assert res_ok.status_code == 200
    token = res_ok.json()["access_token"]
    assert token

    # Invalid password
    res_bad = client.post(
        "/api/auth/login",
        json={"email": "login_test@example.com", "password": "wrongpassword"},
    )
    assert res_bad.status_code == 401
    assert "Invalid email or password" in res_bad.json()["detail"]

    # Non-existent email
    res_no = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@example.com", "password": "correctpassword"},
    )
    assert res_no.status_code == 401


def test_get_me_authenticated_and_unauthenticated(client):
    """Verify /api/auth/me returns profile when token is valid and 401 when missing/invalid."""
    # Unauthenticated
    res_unauth = client.get("/api/auth/me")
    assert res_unauth.status_code == 401

    # Invalid token
    res_inv = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.value"})
    assert res_inv.status_code == 401

    # Valid token
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "me_test@example.com",
            "password": "password123",
            "display_name": "Me User",
        },
    )
    token = reg.json()["access_token"]

    res_auth = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_auth.status_code == 200
    assert res_auth.json()["email"] == "me_test@example.com"
    assert res_auth.json()["display_name"] == "Me User"
