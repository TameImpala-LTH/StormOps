# 12_DECISION_LOG.md

# Decision Log

## 1. Purpose

This document records important architectural, product, and implementation decisions made during WeatherGPT development.

Only meaningful decisions that affect the project should be recorded here.

---

## 2. Decision Format

Each decision should contain:

- **Date**
- **Decision**
- **Reason**
- **Impact**

Example:

```text
Date: YYYY-MM-DD

Decision:
Use FastAPI for the backend.

Reason:
Provides a lightweight Python backend suitable for rapid API and AI integration.

Impact:
Frontend communicates with a dedicated backend responsible for weather and AI services.