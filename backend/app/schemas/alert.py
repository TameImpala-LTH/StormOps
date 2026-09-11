"""Pydantic schemas for deterministic severe weather alerts and risk advisories."""

from typing import Any, List
from pydantic import BaseModel, Field


class AlertFactor(BaseModel):
    """Triggering metric factor for a severe weather alert."""

    metric: str = Field(..., description="Meteorological metric name (e.g. wind_speed, precipitation, weather_code)")
    value: Any = Field(..., description="Observed value during target period")
    threshold: str = Field(..., description="Threshold benchmark triggering alert")


class WeatherAlert(BaseModel):
    """Structured deterministic weather alert or risk advisory."""

    id: str = Field(..., description="Unique alert identifier")
    severity: str = Field(..., description="Alert severity level: warning | watch | advisory")
    category: str = Field(..., description="Alert category: thunderstorm | heavy_rain | high_wind | extreme_heat | extreme_cold | heavy_snow | fog | severe_weather")
    title: str = Field(..., description="Short headline title for alert")
    summary: str = Field(..., description="Data-grounded summary description of risk")
    factors: List[AlertFactor] = Field(default_factory=list, description="List of triggering meteorological factors")
