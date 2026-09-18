"""Pydantic schemas for natural language query request and response with session tracking."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional
from pydantic import BaseModel, Field

from app.schemas.advisory import AdvisoryResponse
from app.schemas.alert import WeatherAlert
from app.schemas.decision import DecisionResponse
from app.schemas.event import EnvironmentalEvent
from app.schemas.weather import CurrentWeather, HourlyForecast, LocationCoordinates

if TYPE_CHECKING:
    from app.schemas.comparison import ComparisonResponse


class CoordinateInput(BaseModel):
    """Structured latitude and longitude coordinates from device geolocation."""

    latitude: float = Field(..., description="Latitude coordinate from device geolocation")
    longitude: float = Field(..., description="Longitude coordinate from device geolocation")


class QueryRequest(BaseModel):
    """Request model for natural language weather query endpoint."""

    message: str = Field(..., min_length=2, description="User natural language weather query")
    session_id: Optional[str] = Field("default", description="Optional in-memory session identifier for context tracking")
    location: Optional[CoordinateInput] = Field(None, description="Optional structured device coordinates")
    language: Optional[str] = Field("auto", description="Optional client language hint ('en', 'hi', 'bn', 'ta', 'te', 'mr', or 'auto')")


class ExtractedQueryInfo(BaseModel):
    """Structured intent and entity extraction from natural language query."""

    original_query: str = Field(..., description="Original user query text")
    intent: str = Field(..., description="Extracted user intent (e.g. rain_query, umbrella_recommendation, comparison)")
    extracted_location: Optional[str] = Field(None, description="Location name extracted from query, if present")
    extracted_location_a: Optional[str] = Field(None, description="First location name for comparison queries")
    extracted_location_b: Optional[str] = Field(None, description="Second location name for comparison queries")
    comparison_goal: Optional[str] = Field(None, description="Optional comparison goal (e.g. travel, outdoor_activity, rain, temperature)")
    date_context: str = Field("today", description="Extracted date context (e.g. today, tomorrow)")
    time_period: str = Field("current", description="Extracted time period (e.g. now, morning, evening, night)")
    language: str = Field("en", description="Identified or active language code ('en', 'hi', 'bn', 'ta', 'te', 'mr')")


class GeocodedLocationSchema(BaseModel):
    """Resolved location coordinates from geocoding service."""

    name: str = Field(..., description="City or region display name")
    country: str = Field(..., description="Country name")
    country_code: Optional[str] = Field(None, description="ISO 3166-1 alpha-2 country code (e.g. 'GB', 'FR', 'US', 'IN')")
    admin1: Optional[str] = Field(None, description="State or administrative region")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    timezone: str = Field("UTC", description="Resolved timezone name")


class TargetPeriodWeather(BaseModel):
    """Normalized weather metrics for the user's selected date and time period."""

    period_label: str = Field(..., description="Human-readable period label (e.g. 'tomorrow evening', 'today', 'tonight')")
    temperature: float = Field(..., description="Representative temperature in Celsius")
    feels_like: float = Field(..., description="Representative feels-like temperature in Celsius")
    condition: str = Field(..., description="Weather condition text")
    weather_code: int = Field(..., description="WMO weather code")
    humidity: int = Field(..., description="Relative humidity percentage")
    wind_speed: float = Field(..., description="Wind speed in km/h")
    precipitation: float = Field(..., description="Precipitation amount in mm")
    precipitation_probability: int = Field(..., description="Precipitation probability percentage (0-100)")
    rain_duration_hours: int = Field(0, description="Count of hours in period meeting precipitation evidence criteria")
    peak_hour: Optional[str] = Field(None, description="Time label of strongest precipitation probability / amount")
    total_precipitation: float = Field(0.0, description="Total accumulated precipitation across period in mm")


class QueryResponse(BaseModel):
    """Full orchestrated response for natural language query."""

    query: ExtractedQueryInfo
    location: Optional[GeocodedLocationSchema] = Field(None, description="Resolved location coordinates if available")
    current: Optional[CurrentWeather] = Field(None, description="Current weather data if available")
    period_weather: Optional[TargetPeriodWeather] = Field(None, description="Normalized weather metrics for selected period")
    period_forecast: Optional[List[HourlyForecast]] = Field(None, description="Hourly forecast items matching requested date and time period")
    forecast: Optional[List[HourlyForecast]] = Field(None, description="24-hour forecast items if applicable")
    decision: Optional[DecisionResponse] = Field(None, description="Structured decision engine recommendation")
    alerts: Optional[List[WeatherAlert]] = Field(default_factory=list, description="Structured severe weather alerts or risk advisories")
    environmental_events: Optional[List[EnvironmentalEvent]] = Field(default_factory=list, description="Structured event-based environmental advisories")
    official_advisories: Optional[List[AdvisoryResponse]] = Field(default_factory=list, description="Active official hazard advisories for resolved location")
    comparison: Optional[ComparisonResponse] = Field(None, description="Structured dual-location weather comparison if applicable")
    summary: str = Field(..., description="Grounded natural language interpretation or clarification request")
    needs_clarification: bool = Field(False, description="True if missing location or required information")
    language: str = Field("en", description="Active response language code ('en', 'hi', 'bn')")
    session_id: Optional[str] = Field(None, description="Session ID used for context tracking")
    timestamp: str = Field(..., description="Response generation timestamp")



# Resolve forward reference after comparison module import
from app.schemas.comparison import ComparisonResponse  # noqa: E402

QueryResponse.model_rebuild()
