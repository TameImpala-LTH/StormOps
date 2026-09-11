"""Unit tests for user-owned saved locations with strict data isolation."""

import app.core.compat  # noqa: F401
import pytest


def test_saved_locations_crud_and_duplicate_prevention(client):
    """Verify saved location creation, listing, duplicate coordinate prevention, and deletion."""
    # Register user
    reg = client.post(
        "/api/auth/register",
        json={"email": "loc_user@example.com", "password": "password123", "display_name": "Loc User"},
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Initial list is empty
    initial_res = client.get("/api/locations", headers=headers)
    assert initial_res.status_code == 200
    assert len(initial_res.json()) == 0

    # Save Kolkata
    create_res = client.post(
        "/api/locations",
        json={"name": "Kolkata", "latitude": 22.5726, "longitude": 88.3639, "country": "India"},
        headers=headers,
    )
    assert create_res.status_code == 201
    loc_id = create_res.json()["id"]
    assert create_res.json()["name"] == "Kolkata"

    # Try saving duplicate coordinates for the same user -> returns existing without erroring
    dup_res = client.post(
        "/api/locations",
        json={"name": "Kolkata City", "latitude": 22.57264, "longitude": 88.36392, "country": "India"},
        headers=headers,
    )
    assert dup_res.status_code == 201
    assert dup_res.json()["id"] == loc_id

    # List should still have 1 item
    list_res = client.get("/api/locations", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # Save second location (Mumbai)
    create_res2 = client.post(
        "/api/locations",
        json={"name": "Mumbai", "latitude": 19.0760, "longitude": 72.8777, "country": "India"},
        headers=headers,
    )
    assert create_res2.status_code == 201

    list_res2 = client.get("/api/locations", headers=headers)
    assert len(list_res2.json()) == 2

    # Delete Kolkata
    del_res = client.delete(f"/api/locations/{loc_id}", headers=headers)
    assert del_res.status_code == 204

    # List should now have 1 item
    list_res3 = client.get("/api/locations", headers=headers)
    assert len(list_res3.json()) == 1
    assert list_res3.json()[0]["name"] == "Mumbai"


def test_saved_locations_strict_user_data_isolation(client):
    """Verify User A cannot see or delete User B's saved locations."""
    # Register User A
    reg_a = client.post(
        "/api/auth/register",
        json={"email": "loc_a@example.com", "password": "password123", "display_name": "User A"},
    )
    token_a = reg_a.json()["access_token"]

    # Register User B
    reg_b = client.post(
        "/api/auth/register",
        json={"email": "loc_b@example.com", "password": "password123", "display_name": "User B"},
    )
    token_b = reg_b.json()["access_token"]

    # User A saves Darjeeling
    create_a = client.post(
        "/api/locations",
        json={"name": "Darjeeling", "latitude": 27.0410, "longitude": 88.2663, "country": "India"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert create_a.status_code == 201
    loc_a_id = create_a.json()["id"]

    # User B lists saved locations -> sees 0 locations
    list_b = client.get("/api/locations", headers={"Authorization": f"Bearer {token_b}"})
    assert list_b.status_code == 200
    assert len(list_b.json()) == 0

    # User B attempts to delete User A's saved location -> returns 404
    del_b = client.delete(f"/api/locations/{loc_a_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert del_b.status_code == 404

    # User A's location remains intact
    list_a = client.get("/api/locations", headers={"Authorization": f"Bearer {token_a}"})
    assert len(list_a.json()) == 1


def test_anonymous_user_cannot_access_saved_locations(client):
    """Verify anonymous unauthenticated users are rejected with 401 from saved locations endpoints."""
    # Anonymous GET
    res_get = client.get("/api/locations")
    assert res_get.status_code == 401

    # Anonymous POST
    res_post = client.post(
        "/api/locations",
        json={"name": "Kolkata", "latitude": 22.5726, "longitude": 88.3639, "country": "India"},
    )
    assert res_post.status_code == 401

    # Anonymous DELETE
    res_del = client.delete("/api/locations/some-random-id")
    assert res_del.status_code == 401


def test_saved_location_with_region_label_preserved(client):
    """Verify region-level names such as 'Goa (Region)' and 'Kerala (Region)' are preserved verbatim."""
    # Register user
    reg = client.post(
        "/api/auth/register",
        json={"email": "region_loc_user@example.com", "password": "password123", "display_name": "Region User"},
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Save Kerala (Region)
    res = client.post(
        "/api/locations",
        json={"name": "Kerala (Region)", "latitude": 10.8505, "longitude": 76.2711, "country": "India"},
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Kerala (Region)"
    assert data["latitude"] == 10.8505
    assert data["longitude"] == 76.2711
    assert data["country"] == "India"

    # Fetch list and confirm
    list_res = client.get("/api/locations", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 1
    assert items[0]["name"] == "Kerala (Region)"

