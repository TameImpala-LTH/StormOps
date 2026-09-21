"""Pydantic schemas for normalized weather data."""

from typing import List, Optional
from pydantic import BaseModel, Field


class LocationCoordinates(BaseModel):
    """Location geographic coordinates."""

    latitude: float = Field(..., description="Latitude of location", ge=-90.0, le=90.0)
    longitude: float = Field(..., description="Longitude of location", ge=-180.0, le=180.0)
    name: Optional[str] = Field(None, description="Location display name if available")
    timezone: Optional[str] = Field(None, description="Timezone name")


class CurrentWeather(BaseModel):
    """Normalized current weather observation."""

    temperature: Optional[float] = Field(None, description="Current temperature in Celsius")
    feels_like: Optional[float] = Field(None, description="Apparent feels-like temperature in Celsius")
    condition: str = Field(..., description="Human-readable weather condition text")
    weather_code: int = Field(..., description="WMO weather interpretation code")
    humidity: int = Field(..., description="Relative humidity percentage (0-100)")
    wind_speed: Optional[float] = Field(None, description="Wind speed in km/h")
    precipitation: Optional[float] = Field(None, description="Precipitation amount in mm")
    precipitation_probability: Optional[int] = Field(
        None, description="Precipitation probability percentage (0-100)"
    )
    time: str = Field(..., description="Observation time ISO string")



class HourlyForecast(BaseModel):
    """Normalized hourly forecast item."""

    time: str = Field(..., description="Forecast hour time ISO string")
    temperature: float = Field(..., description="Temperature in Celsius")
    condition: str = Field(..., description="Human-readable weather condition text")
    weather_code: int = Field(..., description="WMO weather interpretation code")
    precipitation_probability: Optional[int] = Field(
        None, description="Precipitation probability percentage (0-100)"
    )
    precipitation: float = Field(..., description="Precipitation in mm")
    wind_speed: float = Field(..., description="Wind speed in km/h")
    humidity: Optional[int] = Field(None, description="Relative humidity percentage (0-100)")
    feels_like: Optional[float] = Field(None, description="Apparent feels-like temperature in Celsius")


class CurrentWeatherResponse(BaseModel):
    """API response model for current weather endpoint."""

    location: LocationCoordinates
    current: CurrentWeather
    source: str = Field("open-meteo", description="Data provider source")
    timestamp: str = Field(..., description="Response generation timestamp")


class ForecastResponse(BaseModel):
    """API response model for weather forecast endpoint."""

    location: LocationCoordinates
    hourly: List[HourlyForecast]
    source: str = Field("open-meteo", description="Data provider source")
    timestamp: str = Field(..., description="Response generation timestamp")
