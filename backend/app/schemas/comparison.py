"""Pydantic schemas for deterministic location and weather decision comparison."""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field

from app.schemas.alert import WeatherAlert
from app.schemas.query import GeocodedLocationSchema, TargetPeriodWeather


class ComparisonMetricDifference(BaseModel):
    """Comparative breakdown of a specific meteorological metric between location A and B."""

    metric: str = Field(..., description="Metric name (e.g. precipitation_probability, temperature, wind_speed)")
    value_a: Any = Field(..., description="Observed value at Location A")
    value_b: Any = Field(..., description="Observed value at Location B")
    better_location: Optional[str] = Field("equal", description="Location key with more favorable value: 'a' | 'b' | 'equal'")
    impact_note: str = Field(..., description="Short explanation of metric impact")


class ComparisonDecision(BaseModel):
    """Structured deterministic recommendation resulting from location comparison."""

    recommended_location: str = Field(..., description="Recommended location display name or 'broadly_similar'")
    recommended_key: str = Field(..., description="Recommended location key: 'a' | 'b' | 'equal'")
    confidence: str = Field(..., description="Decision confidence: 'high' | 'medium' | 'low'")
    summary: str = Field(..., description="Concise summary headline of recommendation")
    winner_reason: str = Field(..., description="Key decision factors explaining recommendation")
    factors: List[ComparisonMetricDifference] = Field(default_factory=list, description="Metric comparison breakdown")


class ComparisonResponse(BaseModel):
    """Orchestrated comparison dataset for dual-location weather comparison."""

    location_a: GeocodedLocationSchema = Field(..., description="Resolved location A coordinates and display metadata")
    location_b: GeocodedLocationSchema = Field(..., description="Resolved location B coordinates and display metadata")
    target_period: str = Field(..., description="Human readable target weather period for both locations")
    period_weather_a: TargetPeriodWeather = Field(..., description="Normalized weather metrics for location A")
    period_weather_b: TargetPeriodWeather = Field(..., description="Normalized weather metrics for location B")
    decision: ComparisonDecision = Field(..., description="Structured deterministic decision recommendation")
    alerts_a: List[WeatherAlert] = Field(default_factory=list, description="Active severe weather alerts for location A")
    alerts_b: List[WeatherAlert] = Field(default_factory=list, description="Active severe weather alerts for location B")
    comparison_goal: str = Field("general", description="Target activity or decision goal (e.g. travel, outdoor_activity, rain, temperature)")
