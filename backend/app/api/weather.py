"""Weather API routes for current conditions, forecast retrieval, and natural language query processing."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.schemas.event import EnvironmentalEvent
from app.schemas.query import QueryRequest, QueryResponse
from app.schemas.weather import CurrentWeatherResponse, ForecastResponse
from app.services.event_service import event_service
from app.services.query_service import query_service
from app.services.weather_service import weather_service

router = APIRouter()


def validate_coordinates(latitude: float, longitude: float) -> None:
    """Validate latitude and longitude ranges, raising HTTP 400 for out-of-bounds values."""
    if not (-90.0 <= latitude <= 90.0):
        raise HTTPException(
            status_code=400,
            detail=f"Latitude must be between -90.0 and 90.0. Received: {latitude}",
        )
    if not (-180.0 <= longitude <= 180.0):
        raise HTTPException(
            status_code=400,
            detail=f"Longitude must be between -180.0 and 180.0. Received: {longitude}",
        )


@router.get("/current", response_model=CurrentWeatherResponse)
async def get_current_weather(
    latitude: float = Query(..., description="Latitude coordinate (-90 to 90)"),
    longitude: float = Query(..., description="Longitude coordinate (-180 to 180)"),
):
    """Retrieve normalized current weather observation for specified coordinates."""
    validate_coordinates(latitude, longitude)
    return await weather_service.get_current_weather(latitude, longitude)


@router.get("/forecast", response_model=ForecastResponse)
async def get_weather_forecast(
    latitude: float = Query(..., description="Latitude coordinate (-90 to 90)"),
    longitude: float = Query(..., description="Longitude coordinate (-180 to 180)"),
    hours: int = Query(24, description="Forecast duration in hours (1 to 168)"),
):
    """Retrieve normalized hourly weather forecast for specified coordinates and hours."""
    validate_coordinates(latitude, longitude)
    if not (1 <= hours <= 168):
        raise HTTPException(
            status_code=400,
            detail=f"Requested forecast hours must be between 1 and 168. Received: {hours}",
        )
    return await weather_service.get_forecast(latitude, longitude, hours)


@router.post("/query", response_model=QueryResponse)
async def process_natural_language_query(request: QueryRequest):
    """Process natural language weather query with entity extraction, session context, geocoding, weather retrieval, and summary."""
    sess_id = request.session_id or "default"
    return await query_service.process_query(request.message, session_id=sess_id)


@router.get("/events", response_model=List[EnvironmentalEvent])
async def get_environmental_events(
    location: str = Query(..., description="Location name to lookup environmental events for"),
):
    """Retrieve verified upcoming or active environmental/festival events for a location."""
    if not location or not location.strip():
        return []
    return event_service.get_location_events(location.strip())
