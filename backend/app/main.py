"""WeatherGPT FastAPI application entry point."""

import app.core.compat  # noqa: F401  — must be imported before FastAPI/pydantic

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.history import router as history_router
from app.api.saved_locations import router as saved_locations_router
from app.api.speech import router as speech_router
from app.api.weather import router as weather_router
from app.api.environmental import router as environmental_router
from app.api.advisory import router as advisory_router
from app.api.diagnostics import router as diagnostics_router
from app.core.config import settings

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Log safe startup diagnostics without logging actual secrets."""
    msg = (
        f"[Startup Diagnostics] AI_PROVIDER: {settings.ai_provider} | "
        f"AI_API_KEY configured: {bool(settings.ai_api_key and settings.ai_api_key.strip())} | "
        f"AI_MODEL: {settings.ai_model} | "
        f"AI_TRANSCRIPTION_MODEL: {settings.ai_transcription_model}"
    )
    print(msg, flush=True)
    logger.info(msg)
    yield
    # Clean up persistent clients on shutdown
    try:
        from app.services.llm_service import llm_service
        await llm_service.aclose()
    except Exception as exc:
        logger.debug(f"LLM client shutdown cleanup: {exc}")


app = FastAPI(
    title=settings.app_name,
    docs_url="/docs" if settings.app_debug else None,
    redoc_url="/redoc" if settings.app_debug else None,
    lifespan=lifespan,
)

# CORS middleware — allows the React dev server and production frontend to call the API
origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"], include_in_schema=False)
async def root_health():
    """Root health check endpoint for cloud host health checks (e.g. Render)."""
    return {
        "status": "healthy",
        "service": "weathergpt-backend",
    }


# Register routes
app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(history_router, prefix="/api/history", tags=["history"])
app.include_router(saved_locations_router, prefix="/api/locations", tags=["saved-locations"])
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(speech_router, prefix="/api/speech", tags=["speech"])
app.include_router(weather_router, prefix="/api/weather", tags=["weather"])
app.include_router(advisory_router, prefix="/api/weather", tags=["advisories"])
app.include_router(environmental_router, prefix="/api/environmental", tags=["environmental"])
app.include_router(diagnostics_router, prefix="/api/diagnostics", tags=["diagnostics"])


@app.exception_handler(OperationalError)
async def operational_error_handler(request: Request, exc: OperationalError):
    """Handle database operational errors gracefully with a 503 Service Unavailable."""
    logger.error(f"Database OperationalError on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": "Database service is currently unavailable. Please check database connection."},
    )
