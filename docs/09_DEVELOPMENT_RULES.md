# 09_DEVELOPMENT_RULES.md

# Development Rules

## 1. Purpose

These rules define how WeatherGPT should be developed, tested, documented, and maintained during the hackathon.

---

## 2. Implementation Priority

Development should follow this order:

1. Core functionality
2. Reliable weather data
3. Conversational interaction
4. Decision engine
5. Main visual experience
6. Supporting features
7. Polish and animations
8. Stretch features

Do not sacrifice working core functionality for additional features.

---

## 3. Functional vs Demo Features

Features should be clearly treated as either:

- **Functional** — works using real data and real application logic.
- **Demo-oriented** — simplified implementation intended primarily for presentation.
- **Future-ready** — interface or architecture prepared for later implementation.

Do not present demo-oriented functionality as fully implemented production functionality.

---

## 4. AI Development Rule

AI must remain grounded in actual weather data.

Never hardcode fabricated weather responses merely to make the AI appear functional.

If a required external service is unavailable, provide a clear fallback rather than inventing results.

---

## 5. Frontend Rules

The frontend should:

- Remain minimal and visually focused.
- Avoid unnecessary UI elements.
- Avoid generic dashboard layouts.
- Use reusable components.
- Keep API logic separate from presentation.
- Handle loading, empty, and error states.
- Avoid hardcoded weather information.

---

## 6. Backend Rules

The backend should:

- Keep external API integrations isolated.
- Normalize provider responses.
- Validate incoming requests.
- Return consistent API responses.
- Keep secrets server-side.
- Handle external service failures gracefully.
- Avoid coupling application logic directly to one provider.

---

## 7. Code Quality

Code should favor:

- Clear naming
- Small focused functions
- Reusable components
- Explicit data structures
- Minimal duplication
- Simple architecture

Avoid unnecessary abstractions that do not provide value during the hackathon.

---

## 8. Environment Variables

Secrets and API keys must never be committed to source control.

Use environment variables for:

- Weather API keys
- AI API keys
- Other external service credentials

Provide an `.env.example` containing required variable names without real secrets.

---

## 9. Error Handling

Every external dependency should have a failure path.

The application should gracefully handle:

- Invalid locations
- Invalid queries
- Weather API failures
- AI API failures
- Network failures
- Missing forecast data
- Rate limits

Errors shown to users should be understandable and actionable.

---

## 10. Testing

At minimum, test:

- Backend health endpoint
- Weather API integration
- Location resolution
- Chat request flow
- Decision generation
- Invalid requests
- External API failure handling
- Main frontend interaction

Critical functionality should be tested before adding major new features.

---

## 11. Documentation

Important implementation decisions should be documented.

The development log should record significant work performed by Antigravity, including:

- Date and time
- Changes made
- Files affected
- Tests performed
- Results
- Issues and fixes
- Decisions
- Current status

---

## 12. Git Rules

Use Git regularly.

Commits should represent meaningful working changes.

Avoid committing:

- API keys
- `.env` files containing secrets
- Generated build artifacts
- Unnecessary temporary files
- Large unrelated files

---

## 13. Antigravity Workflow

For significant implementation tasks:

1. Inspect the existing project.
2. Understand the current architecture.
3. Make the smallest appropriate change.
4. Run relevant tests or checks.
5. Verify the result.
6. Update documentation when necessary.
7. Record the work in the development log.

Antigravity should not rewrite working systems unnecessarily.

---

## 14. Scope Control

New features should be evaluated against:

- Hackathon time remaining
- Demo value
- Implementation effort
- Reliability
- Dependency risk

If a feature threatens the stability of the core product, defer it.

---

## 15. Core Development Principle

> **Build a small, reliable WeatherGPT first. Then make it impressive.**

---

## 16. Multi-User Consumer Architecture

StormOps is a public multi-user application, not an internal or administrative tool.

1. Anyone can create an independent account with isolated personal history and saved locations.
2. There are no admin accounts, admin dashboards, or pre-seeded users.
3. Passwords must be hashed using industry-standard bcrypt.
4. Tokens must be signed JWTs with explicit expiration; no passwords or secret keys may be logged or sent to clients.
5. The public, anonymous WeatherGPT experience must never require an account to check weather. Login is purely optional for saving history and favorite places.