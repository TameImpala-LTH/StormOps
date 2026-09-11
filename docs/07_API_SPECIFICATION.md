# 07_API_SPECIFICATION.md

# API Specification

## 1. Purpose

This document defines the API contract between the WeatherGPT frontend and backend.

The API should remain simple, predictable, and sufficient for the hackathon MVP.

---

## 2. Base URL

Development:

```text
http://localhost:8000
```

---

## 3. Endpoints

### 3.1 Authentication

#### `POST /api/auth/register`
Creates a new user account.
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "secretpassword",
    "display_name": "Jane Doe"
  }
  ```
- **Response** `201 Created`:
  ```json
  {
    "access_token": "<jwt_token>",
    "token_type": "bearer",
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "display_name": "Jane Doe",
      "created_at": "ISO-8601"
    }
  }
  ```

#### `POST /api/auth/login`
Authenticates an existing user and returns a 60-minute JWT access token.
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "secretpassword"
  }
  ```
- **Response** `200 OK`:
  ```json
  {
    "access_token": "<jwt_token>",
    "token_type": "bearer",
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "display_name": "Jane Doe",
      "created_at": "ISO-8601"
    }
  }
  ```

#### `GET /api/auth/me`
Retrieves the currently authenticated user's profile.
- **Headers**: `Authorization: Bearer <token>`
- **Response** `200 OK`:
  ```json
  {
    "id": "uuid",
    "email": "user@example.com",
    "display_name": "Jane Doe",
    "created_at": "ISO-8601"
  }
  ```

---

### 3.2 Conversation History

#### `GET /api/history`
Returns list of conversations owned by the authenticated user ordered by update time descending.
- **Headers**: `Authorization: Bearer <token>`
- **Response** `200 OK`:
  ```json
  [
    {
      "id": "uuid",
      "title": "Kolkata weather",
      "location_name": "Kolkata",
      "created_at": "ISO-8601",
      "updated_at": "ISO-8601"
    }
  ]
  ```

#### `GET /api/history/{conversation_id}`
Returns full message history for a conversation owned by the authenticated user.
- **Headers**: `Authorization: Bearer <token>`
- **Response** `200 OK`:
  ```json
  {
    "id": "uuid",
    "title": "Kolkata weather",
    "location_name": "Kolkata",
    "created_at": "ISO-8601",
    "updated_at": "ISO-8601",
    "messages": [
      {
        "id": "uuid",
        "role": "user",
        "content": "What is the weather in Kolkata?",
        "created_at": "ISO-8601"
      },
      {
        "id": "uuid",
        "role": "assistant",
        "content": "In Kolkata today, expect mild temperatures around 24°C...",
        "created_at": "ISO-8601"
      }
    ]
  }
  ```

#### `DELETE /api/history/{conversation_id}`
Deletes a conversation and its messages.
- **Headers**: `Authorization: Bearer <token>`
- **Response** `204 No Content`

---

### 3.3 Saved / Favorite Locations

#### `GET /api/locations`
Returns saved locations for the authenticated user.
- **Headers**: `Authorization: Bearer <token>`
- **Response** `200 OK`:
  ```json
  [
    {
      "id": "uuid",
      "user_id": "uuid",
      "name": "Tokyo",
      "latitude": 35.6895,
      "longitude": 139.6917,
      "country": "Japan",
      "created_at": "ISO-8601"
    }
  ]
  ```

#### `POST /api/locations`
Saves a new location (idempotent / prevents duplicate coordinates within 0.001 deg).
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "name": "Tokyo",
    "latitude": 35.6895,
    "longitude": 139.6917,
    "country": "Japan"
  }
  ```
- **Response** `201 Created`

#### `DELETE /api/locations/{location_id}`
Removes a saved location.
- **Headers**: `Authorization: Bearer <token>`
- **Response** `204 No Content`

---

### 3.4 Conversational Weather Chat

#### `POST /api/chat`
Processes natural language weather queries. Supports both anonymous visitors and authenticated users.
- **Optional Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "message": "Will it rain in Paris tomorrow?",
    "session_id": "optional-session-or-conversation-uuid",
    "location": { "latitude": 48.8566, "longitude": 2.3522 },
    "language": "auto"
  }
  ```
- **Response** `200 OK`: Returns full `QueryResponse` with meteorological data, decision evaluation, severe weather alerts, and interpretation. If authenticated, saves message history and assigns persistent `session_id`.