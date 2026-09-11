"""Weather service for communicating with Open-Meteo weather API and normalizing responses."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict

from fastapi import HTTPException
import httpx

from app.core.config import settings
from app.schemas.weather import (
    CurrentWeather,
    CurrentWeatherResponse,
    ForecastResponse,
    HourlyForecast,
    LocationCoordinates,
)

logger = logging.getLogger(__name__)

# WMO Weather interpretation codes (WW) mapping
WMO_CODE_MAP: Dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def get_condition_text(weather_code: int) -> str:
    """Return human readable condition text for WMO code."""
    return WMO_CODE_MAP.get(weather_code, "Unknown weather condition")


class WeatherService:
    """Service handling weather data retrieval and normalization."""

    def __init__(self, base_url: str = None, client: httpx.AsyncClient = None):
        self.base_url = base_url or settings.weather_api_base_url or "https://api.open-meteo.com/v1/forecast"
        self._client = client

    async def _fetch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Internal helper to execute HTTP GET request against weather provider."""
        timeout = httpx.Timeout(10.0, connect=5.0)
        try:
            if self._client:
                response = await self._client.get(self.base_url, params=params, timeout=timeout)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.get(self.base_url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as exc:
            logger.error(f"Weather provider timeout: {exc}")
            raise HTTPException(status_code=504, detail="Weather provider gateway timeout")
        except httpx.HTTPStatusError as exc:
            logger.error(f"Weather provider HTTP status error: {exc.response.status_code}")
            raise HTTPException(
                status_code=502,
                detail=f"Weather provider returned HTTP error {exc.response.status_code}",
            )
        except httpx.RequestError as exc:
            logger.error(f"Weather provider network request error: {exc}")
            raise HTTPException(status_code=502, detail="Weather provider network request failed")

    async def get_current_weather(
        self, latitude: float, longitude: float
    ) -> CurrentWeatherResponse:
        """Retrieve current weather observation for specified coordinates."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
            "hourly": "precipitation_probability",
            "forecast_days": 1,
            "timezone": "auto",
        }

        data = await self._fetch(params)

        try:
            current_raw = data["current"]
            tz_name = data.get("timezone", "UTC")

            # Extract precipitation probability from current hour if present
            precip_prob = None
            hourly_raw = data.get("hourly", {})
            hourly_times = hourly_raw.get("time", [])
            hourly_probs = hourly_raw.get("precipitation_probability", [])
            current_time = current_raw.get("time")

            if current_time and hourly_times and current_time in hourly_times:
                idx = hourly_times.index(current_time)
                if idx < len(hourly_probs) and hourly_probs[idx] is not None:
                    precip_prob = int(hourly_probs[idx])
            elif hourly_probs and len(hourly_probs) > 0 and hourly_probs[0] is not None:
                precip_prob = int(hourly_probs[0])

            code = int(current_raw["weather_code"])
            current = CurrentWeather(
                temperature=float(current_raw["temperature_2m"]),
                feels_like=float(current_raw["apparent_temperature"]),
                condition=get_condition_text(code),
                weather_code=code,
                humidity=int(current_raw["relative_humidity_2m"]),
                wind_speed=float(current_raw["wind_speed_10m"]),
                precipitation=float(current_raw["precipitation"]),
                precipitation_probability=precip_prob,
                time=str(current_raw["time"]),
            )

            location = LocationCoordinates(
                latitude=latitude,
                longitude=longitude,
                timezone=tz_name,
            )

            return CurrentWeatherResponse(
                location=location,
                current=current,
                source="open-meteo",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        except (KeyError, ValueError, TypeError) as exc:
            logger.error(f"Failed to parse provider response: {exc}")
            raise HTTPException(
                status_code=502, detail="Failed to parse weather provider response"
            )

    async def get_forecast(
        self, latitude: float, longitude: float, hours: int = 24
    ) -> ForecastResponse:
        """Retrieve hourly forecast data for specified coordinates and hours."""
        forecast_days = max(1, min(7, (hours + 23) // 24))
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m",
            "forecast_days": forecast_days,
            "timezone": "auto",
        }

        data = await self._fetch(params)

        try:
            hourly_raw = data["hourly"]
            tz_name = data.get("timezone", "UTC")

            times = hourly_raw["time"]
            temperatures = hourly_raw["temperature_2m"]
            apparent_temps = hourly_raw.get("apparent_temperature", [])
            codes = hourly_raw["weather_code"]
            precip_probs = hourly_raw.get("precipitation_probability", [])
            precips = hourly_raw["precipitation"]
            winds = hourly_raw["wind_speed_10m"]

            hourly_items = []
            max_idx = min(len(times), hours)

            for i in range(max_idx):
                code = int(codes[i])
                prob = (
                    int(precip_probs[i])
                    if (i < len(precip_probs) and precip_probs[i] is not None)
                    else None
                )
                app_temp = (
                    float(apparent_temps[i])
                    if (i < len(apparent_temps) and apparent_temps[i] is not None)
                    else float(temperatures[i])
                )

                item = HourlyForecast(
                    time=str(times[i]),
                    temperature=float(temperatures[i]),
                    feels_like=app_temp,
                    condition=get_condition_text(code),
                    weather_code=code,
                    precipitation_probability=prob,
                    precipitation=float(precips[i]),
                    wind_speed=float(winds[i]),
                )
                hourly_items.append(item)

            location = LocationCoordinates(
                latitude=latitude,
                longitude=longitude,
                timezone=tz_name,
            )

            return ForecastResponse(
                location=location,
                hourly=hourly_items,
                source="open-meteo",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        except (KeyError, ValueError, TypeError) as exc:
            logger.error(f"Failed to parse forecast response: {exc}")
            raise HTTPException(
                status_code=502, detail="Failed to parse weather provider response"
            )


weather_service = WeatherService()
