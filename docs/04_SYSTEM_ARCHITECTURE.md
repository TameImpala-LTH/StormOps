# 04_SYSTEM_ARCHITECTURE.md

# WeatherGPT — System Architecture

## Architecture Goal

WeatherGPT should use a simple, modular architecture that is reliable enough for the hackathon while remaining easy to extend later.

The architecture should separate:

- Frontend
- Backend API
- Query understanding
- Weather data retrieval
- AI processing
- Decision logic
- Alert processing

The system should avoid unnecessary microservices or infrastructure.

## High-Level Architecture

```text
React Frontend (Sidebar, AuthModal, AnswerSurface)
      ↓ (Axios + JWT Bearer Interceptor)
FastAPI Backend
      ↓
┌───────────────────────────────────────┐
│       Public Multi-User Layer         │
│  - User Auth (bcrypt + JWT 60m)       │
│  - Conversation History Persistence   │
│  - Saved Favorite Locations           │
│  - PostgreSQL + SQLAlchemy 2.x        │
└───────────────────────────────────────┘
      ↓
Weather Intelligence Layer
      ↓
┌───────────────┬───────────────┐
│ Weather APIs  │   AI / LLM    │
└───────────────┴───────────────┘
      ↓
Normalized Weather Data
      ↓
Decision / Interpretation
      ↓
Structured Response + History Storage
      ↓
React Frontend
```

## Multi-User & Persistence Architecture (Phase 13)

StormOps is a public, multi-user weather intelligence application. Any visitor can create an account with isolated search history and saved locations:

- **Database**: PostgreSQL with SQLAlchemy 2.x ORM and Alembic migrations.
- **Authentication**: Email/password registration and login with bcrypt hashing and signed JWT tokens (60-minute expiration).
- **History**: Per-user isolated conversations and message logs.
- **Saved Locations**: User-specific favorite locations with coordinate deduplication.
- **Anonymous Continuity**: Unauthenticated visitors retain full WeatherGPT capability without mandatory login.