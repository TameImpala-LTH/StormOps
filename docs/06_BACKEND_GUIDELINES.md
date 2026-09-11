# 06_BACKEND_GUIDELINES.md

# WeatherGPT — Backend Guidelines

## Purpose

The backend is responsible for securely coordinating user queries, weather data, AI processing, decision logic, and responses.

The backend should remain simple, modular, and reliable.

## Technology

Use:

- Python
- FastAPI
- Pydantic
- HTTPX

Additional infrastructure should only be introduced when there is a clear need.

## Responsibilities

The backend should handle:

- API requests
- Request validation
- Query understanding
- Location resolution
- Weather API communication
- Weather data normalization
- AI integration
- Decision logic
- Alert processing
- Error handling
- Response formatting

## Request Flow

A typical request should follow:

```text
User Query
↓
FastAPI Endpoint
↓
Request Validation
↓
Query Processing
↓
Location / Time Resolution
↓
Weather Data Retrieval
↓
Data Validation
↓
AI / Decision Processing
↓
Structured Response