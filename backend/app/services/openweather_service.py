"""OpenWeather fallback provider service."""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple

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


def owm_code_to_wmo(owm_id: int) -> int:
    """Map OpenWeather condition ID to standard WMO weather interpretation code."""
    if 200 <= owm_id <= 232:
        return 95  # Thunderstorm
    elif 300 <= owm_id <= 321:
        return 53  # Moderate drizzle
    elif owm_id == 500:
        return 61  # Slight rain
    elif owm_id == 501:
        return 63  # Moderate rain
    elif 502 <= owm_id <= 504:
        return 65  # Heavy rain
    elif owm_id == 511:
        return 66  # Freezing rain
    elif 520 <= owm_id <= 531:
        return 80  # Rain showers
    elif owm_id == 600:
        return 71  # Slight snow
    elif owm_id == 601:
        return 73  # Moderate snow
    elif 602 <= owm_id <= 622:
        return 75  # Heavy snow
    elif owm_id in (701, 741):
        return 45  # Fog
    elif 711 <= owm_id <= 781:
        return 45  # Atmosphere (mist, smoke, haze, dust)
    elif owm_id == 800:
        return 0  # Clear sky
    elif owm_id == 801:
        return 1  # Mainly clear
    elif owm_id == 802:
        return 2  # Partly cloudy
    elif owm_id in (803, 804):
        return 3  # Overcast
    return 0


# WMO to condition text fallback mapping
WMO_TEXT_MAP: Dict[int, str] = {
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


def _get_wmo_text(wmo_code: int) -> str:
    return WMO_TEXT_MAP.get(wmo_code, "Unknown weather condition")


def _format_timezone_name(tz_shift_seconds: Optional[int]) -> str:
    """Format UTC shift in seconds to an offset string (e.g. UTC+05:30)."""
    if tz_shift_seconds is None:
        return "UTC"
    hours = int(tz_shift_seconds // 3600)
    minutes = int(abs(tz_shift_seconds) % 3600 // 60)
    sign = "+" if tz_shift_seconds >= 0 else "-"
    return f"UTC{sign}{abs(hours):02d}:{minutes:02d}"


class OpenWeatherService:
    """OpenWeather provider service acting as a resilient secondary fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.openweather_api_key
        self.base_url = (base_url or settings.openweather_base_url or "https://api.openweathermap.org/data/2.5").rstrip("/")
        self._client = client

    @property
    def is_configured(self) -> bool:
        """Return True if OpenWeather API key is configured."""
        return bool(self.api_key and self.api_key.strip())

    async def _execute_get(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute HTTP GET to OpenWeather API with credential safety and authentication error handling."""
        if not self.is_configured:
            raise HTTPException(
                status_code=502,
                detail="OpenWeather fallback provider is not configured",
            )

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        query_params = {**params, "appid": self.api_key.strip(), "units": "metric"}
        timeout = httpx.Timeout(10.0, connect=5.0)

        try:
            if self._client:
                response = await self._client.get(url, params=query_params, timeout=timeout)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=query_params, timeout=timeout)

            # Explicitly catch 401/403 auth errors — never retry, never log the API key
            if response.status_code in (401, 403):
                logger.error(
                    "OpenWeather authentication failed (HTTP %s). Check OPENWEATHER_API_KEY configuration.",
                    response.status_code,
                )
                raise HTTPException(
                    status_code=502,
                    detail=f"OpenWeather provider authentication error (HTTP {response.status_code})",
                )

            if response.status_code == 429:
                logger.warning("OpenWeather rate limit reached (HTTP 429).")
                raise HTTPException(
                    status_code=502,
                    detail="OpenWeather rate limit reached",
                )

            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException as exc:
            logger.error(f"OpenWeather timeout: {exc}")
            raise HTTPException(status_code=504, detail="OpenWeather gateway timeout")

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403):
                logger.error(
                    "OpenWeather authentication error (HTTP %s).", exc.response.status_code
                )
                raise HTTPException(
                    status_code=502,
                    detail=f"OpenWeather authentication error (HTTP {exc.response.status_code})",
                )
            logger.error(f"OpenWeather HTTP error: {exc.response.status_code}")
            raise HTTPException(
                status_code=502,
                detail=f"OpenWeather returned HTTP error {exc.response.status_code}",
            )

        except httpx.RequestError as exc:
            logger.error(f"OpenWeather network request error: {exc}")
            raise HTTPException(status_code=502, detail="OpenWeather network request failed")

    async def fetch_current_raw(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch current weather observation from OpenWeather /weather."""
        return await self._execute_get("weather", {"lat": latitude, "lon": longitude})

    async def fetch_forecast_raw(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch 5-day / 3-hour forecast from OpenWeather /forecast."""
        return await self._execute_get("forecast", {"lat": latitude, "lon": longitude})

    def parse_current_weather(
        self, data: Dict[str, Any], latitude: float, longitude: float
    ) -> CurrentWeatherResponse:
        """Parse raw OpenWeather /weather dictionary into normalized CurrentWeatherResponse."""
        try:
            main = data.get("main", {})
            weather_list = data.get("weather", [])
            wind = data.get("wind", {})
            rain = data.get("rain", {})
            snow = data.get("snow", {})

            owm_id = int(weather_list[0].get("id", 800)) if weather_list else 800
            wmo_code = owm_code_to_wmo(owm_id)
            condition_text = _get_wmo_text(wmo_code)

            # Wind speed: OpenWeather units=metric is m/s; convert to km/h (1 m/s = 3.6 km/h)
            wind_speed_kmh = round(float(wind.get("speed", 0.0)) * 3.6, 1)

            # Precipitation in mm
            precip = 0.0
            if isinstance(rain, dict):
                precip = float(rain.get("1h", rain.get("3h", 0.0)))
            if isinstance(snow, dict):
                precip = max(precip, float(snow.get("1h", snow.get("3h", 0.0))))

            dt_val = data.get("dt")
            if dt_val:
                obs_time = datetime.fromtimestamp(dt_val, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M")
            else:
                obs_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")

            tz_name = _format_timezone_name(data.get("timezone"))

            current = CurrentWeather(
                temperature=float(main.get("temp", 0.0)),
                feels_like=float(main.get("feels_like", main.get("temp", 0.0))),
                condition=condition_text,
                weather_code=wmo_code,
                humidity=int(main.get("humidity", 50)),
                wind_speed=wind_speed_kmh,
                precipitation=precip,
                precipitation_probability=None,
                time=obs_time,
            )

            location = LocationCoordinates(
                latitude=latitude,
                longitude=longitude,
                name=data.get("name"),
                timezone=tz_name,
            )

            return CurrentWeatherResponse(
                location=location,
                current=current,
                source="openweather",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        except (KeyError, ValueError, TypeError) as exc:
            logger.error(f"Failed to parse OpenWeather current weather response: {exc}")
            raise HTTPException(
                status_code=502, detail="Failed to parse OpenWeather response"
            )

    def parse_forecast(
        self, data: Dict[str, Any], latitude: float, longitude: float, hours: int = 120
    ) -> ForecastResponse:
        """Parse raw OpenWeather /forecast dictionary into normalized ForecastResponse (up to 5 days)."""
        try:
            city = data.get("city", {})
            tz_name = _format_timezone_name(city.get("timezone"))
            items = data.get("list", [])

            hourly_items: List[HourlyForecast] = []
            for item in items:
                main = item.get("main", {})
                weather_list = item.get("weather", [])
                wind = item.get("wind", {})
                rain = item.get("rain", {})
                snow = item.get("snow", {})

                owm_id = int(weather_list[0].get("id", 800)) if weather_list else 800
                wmo_code = owm_code_to_wmo(owm_id)
                condition_text = _get_wmo_text(wmo_code)

                # Wind speed m/s -> km/h
                wind_speed_kmh = round(float(wind.get("speed", 0.0)) * 3.6, 1)

                # Precipitation
                precip = 0.0
                if isinstance(rain, dict):
                    precip = float(rain.get("3h", 0.0))
                if isinstance(snow, dict):
                    precip = max(precip, float(snow.get("3h", 0.0)))

                # Pop is 0.0 to 1.0 -> convert to percentage
                pop = item.get("pop")
                precip_prob = int(round(float(pop) * 100)) if pop is not None else None

                dt_val = item.get("dt")
                if dt_val:
                    item_time = datetime.fromtimestamp(dt_val, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M")
                else:
                    item_time = item.get("dt_txt", "").replace(" ", "T")[:16]

                hourly_forecast = HourlyForecast(
                    time=item_time,
                    temperature=float(main.get("temp", 0.0)),
                    feels_like=float(main.get("feels_like", main.get("temp", 0.0))),
                    condition=condition_text,
                    weather_code=wmo_code,
                    precipitation_probability=precip_prob,
                    precipitation=precip,
                    wind_speed=wind_speed_kmh,
                )
                hourly_items.append(hourly_forecast)

            location = LocationCoordinates(
                latitude=latitude,
                longitude=longitude,
                name=city.get("name"),
                timezone=tz_name,
            )

            return ForecastResponse(
                location=location,
                hourly=hourly_items,
                source="openweather",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        except (KeyError, ValueError, TypeError) as exc:
            logger.error(f"Failed to parse OpenWeather forecast response: {exc}")
            raise HTTPException(
                status_code=502, detail="Failed to parse OpenWeather response"
            )

    async def fetch_unified_data(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch both current and forecast from OpenWeather and construct unified normalized dictionary."""
        curr_raw, forecast_raw = await asyncio.gather(
            self.fetch_current_raw(latitude, longitude),
            self.fetch_forecast_raw(latitude, longitude),
        )

        curr_res = self.parse_current_weather(curr_raw, latitude, longitude)
        forecast_res = self.parse_forecast(forecast_raw, latitude, longitude)

        # Build unified dictionary matching the internal structure used for caching
        hourly_times = [item.time for item in forecast_res.hourly]
        hourly_temps = [item.temperature for item in forecast_res.hourly]
        hourly_apparent = [
            item.feels_like if item.feels_like is not None else item.temperature
            for item in forecast_res.hourly
        ]
        hourly_codes = [item.weather_code for item in forecast_res.hourly]
        hourly_probs = [item.precipitation_probability for item in forecast_res.hourly]
        hourly_precips = [item.precipitation for item in forecast_res.hourly]
        hourly_winds = [item.wind_speed for item in forecast_res.hourly]

        return {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": curr_res.location.timezone or "UTC",
            "source": "openweather",
            "current": {
                "time": curr_res.current.time,
                "temperature_2m": curr_res.current.temperature,
                "apparent_temperature": curr_res.current.feels_like,
                "relative_humidity_2m": curr_res.current.humidity,
                "weather_code": curr_res.current.weather_code,
                "wind_speed_10m": curr_res.current.wind_speed,
                "precipitation": curr_res.current.precipitation,
            },
            "hourly": {
                "time": hourly_times,
                "temperature_2m": hourly_temps,
                "apparent_temperature": hourly_apparent,
                "weather_code": hourly_codes,
                "precipitation_probability": hourly_probs,
                "precipitation": hourly_precips,
                "wind_speed_10m": hourly_winds,
            },
        }

    async def get_current_weather(self, latitude: float, longitude: float) -> CurrentWeatherResponse:
        """Directly retrieve normalized current weather observation from OpenWeather."""
        raw = await self.fetch_current_raw(latitude, longitude)
        return self.parse_current_weather(raw, latitude, longitude)

    async def get_forecast(
        self, latitude: float, longitude: float, hours: int = 120
    ) -> ForecastResponse:
        """Directly retrieve normalized forecast from OpenWeather."""
        raw = await self.fetch_forecast_raw(latitude, longitude)
        return self.parse_forecast(raw, latitude, longitude, hours=hours)

    async def get_weather_bundle(
        self, latitude: float, longitude: float, hours: int = 120
    ) -> Tuple[CurrentWeatherResponse, ForecastResponse]:
        """Directly retrieve normalized current and forecast bundle from OpenWeather."""
        curr_raw, forecast_raw = await asyncio.gather(
            self.fetch_current_raw(latitude, longitude),
            self.fetch_forecast_raw(latitude, longitude),
        )
        return (
            self.parse_current_weather(curr_raw, latitude, longitude),
            self.parse_forecast(forecast_raw, latitude, longitude, hours=hours),
        )


openweather_service = OpenWeatherService()
