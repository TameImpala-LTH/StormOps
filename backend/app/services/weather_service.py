"""Weather service for communicating with Open-Meteo weather API with caching, deduplication, and resilient 429 backoff."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, Optional

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


@dataclass
class CacheEntry:
    """Weather cache entry with fresh and stale time-to-live boundaries."""

    data: Dict[str, Any]
    created_at: float
    fresh_ttl: float = 600.0  # 10 minutes fresh
    stale_ttl: float = 7200.0  # 2 hours stale fallback

    def is_fresh(self, now: Optional[float] = None) -> bool:
        """Check if cached weather data is within the fresh TTL."""
        curr = now if now is not None else time.monotonic()
        return (curr - self.created_at) <= self.fresh_ttl

    def is_stale_usable(self, now: Optional[float] = None) -> bool:
        """Check if cached data is within the extended stale fallback window."""
        curr = now if now is not None else time.monotonic()
        return (curr - self.created_at) <= self.stale_ttl


class WeatherService:
    """Service handling weather data retrieval, normalization, caching, and 429 resilience."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        fresh_ttl: float = 600.0,
        stale_ttl: float = 7200.0,
        max_retries: int = 3,
        base_retry_delay: float = 0.5,
    ):
        self.base_url = base_url or settings.weather_api_base_url or "https://api.open-meteo.com/v1/forecast"
        self._client = client
        self.fresh_ttl = fresh_ttl
        self.stale_ttl = stale_ttl
        self.max_retries = max_retries
        self.base_retry_delay = base_retry_delay

        # In-memory cache keyed by canonical request signature
        self._cache: Dict[str, CacheEntry] = {}
        # In-flight deduplication tracker: maps cache_key -> asyncio.Future
        self._inflight: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()

    def clear_cache(self) -> None:
        """Clear all in-memory weather cache entries and in-flight tracking."""
        self._cache.clear()
        self._inflight.clear()

    def _make_cache_key(self, params: Dict[str, Any]) -> str:
        """Generate a canonical normalized cache key for weather requests.

        Coordinates are rounded to 2 decimal places (~1.1km grid) to coalesce
        micro-coordinate variations into the same meteorological cell.
        """
        lat = params.get("latitude")
        lon = params.get("longitude")

        lat_str = f"{round(float(lat), 2):.2f}" if lat is not None else "0.00"
        lon_str = f"{round(float(lon), 2):.2f}" if lon is not None else "0.00"

        other_parts = []
        for k in sorted(params.keys()):
            if k not in ("latitude", "longitude"):
                other_parts.append(f"{k}={params[k]}")

        return f"{self.base_url}|{lat_str}|{lon_str}|{'&'.join(other_parts)}"

    async def _execute_http(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute raw HTTP request against Open-Meteo with retry, backoff, and 429 handling."""
        timeout = httpx.Timeout(10.0, connect=5.0)

        for attempt in range(self.max_retries + 1):
            try:
                if self._client:
                    response = await self._client.get(self.base_url, params=params, timeout=timeout)
                else:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(self.base_url, params=params, timeout=timeout)

                # HTTP 429 Rate Limit Handling
                if response.status_code == 429:
                    if attempt < self.max_retries:
                        retry_after = response.headers.get("Retry-After")
                        delay = self.base_retry_delay * (2**attempt)
                        if retry_after:
                            try:
                                parsed = float(retry_after)
                                if 0 < parsed <= 5.0:
                                    delay = parsed
                            except (ValueError, TypeError):
                                pass
                        logger.warning(
                            f"Weather provider 429 rate limit received. Retrying in {delay:.2f}s "
                            f"(attempt {attempt + 1}/{self.max_retries})..."
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error("Weather provider 429 rate limit exceeded after maximum retries.")
                        response.raise_for_status()

                # Transient server errors (500, 502, 503, 504)
                if response.status_code in (500, 502, 503, 504) and attempt < self.max_retries:
                    delay = self.base_retry_delay * (2**attempt)
                    logger.warning(
                        f"Weather provider HTTP {response.status_code}. Retrying in {delay:.2f}s "
                        f"(attempt {attempt + 1}/{self.max_retries})..."
                    )
                    await asyncio.sleep(delay)
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException as exc:
                if attempt < self.max_retries:
                    delay = self.base_retry_delay * (2**attempt)
                    logger.warning(
                        f"Weather provider timeout on attempt {attempt + 1}. Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)
                    continue
                logger.error(f"Weather provider timeout after {self.max_retries} retries: {exc}")
                raise HTTPException(status_code=504, detail="Weather provider gateway timeout")

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    logger.error("Weather provider rate limited (HTTP 429)")
                    raise HTTPException(
                        status_code=502,
                        detail="Weather provider returned HTTP error 429: Rate limit reached. Please try again in a few moments.",
                    )
                logger.error(f"Weather provider HTTP status error: {exc.response.status_code}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Weather provider returned HTTP error {exc.response.status_code}",
                )

            except httpx.RequestError as exc:
                if attempt < self.max_retries:
                    delay = self.base_retry_delay * (2**attempt)
                    logger.warning(
                        f"Weather provider request error on attempt {attempt + 1}. Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)
                    continue
                logger.error(f"Weather provider network request error: {exc}")
                raise HTTPException(status_code=502, detail="Weather provider network request failed")

        raise HTTPException(status_code=502, detail="Weather provider request failed after retries")

    async def _fetch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute weather request with caching, deduplication, and resilient fallback."""
        cache_key = self._make_cache_key(params)

        # 1. Fast path: Fresh cache hit
        entry = self._cache.get(cache_key)
        if entry and entry.is_fresh():
            logger.debug(f"Weather cache hit (fresh): {cache_key}")
            return entry.data

        # 2. In-flight deduplication under lock
        async with self._lock:
            # Re-check under lock
            entry = self._cache.get(cache_key)
            if entry and entry.is_fresh():
                return entry.data

            if cache_key in self._inflight:
                logger.debug(f"Weather request deduplicated (in-flight): {cache_key}")
                inflight_future = self._inflight[cache_key]
                need_spawn = False
            else:
                loop = asyncio.get_running_loop()
                inflight_future = loop.create_future()
                self._inflight[cache_key] = inflight_future
                need_spawn = True

        # If we are the primary caller, execute the network fetch
        if need_spawn:
            try:
                data = await self._execute_http(params)
                # Store fresh cache
                async with self._lock:
                    self._cache[cache_key] = CacheEntry(
                        data=data,
                        created_at=time.monotonic(),
                        fresh_ttl=self.fresh_ttl,
                        stale_ttl=self.stale_ttl,
                    )
                    # Evict oldest entries if cache exceeds 1000 items
                    if len(self._cache) > 1000:
                        oldest_key = next(iter(self._cache))
                        self._cache.pop(oldest_key, None)

                if not inflight_future.done():
                    inflight_future.set_result(data)
                return data

            except Exception as exc:
                # 3. Graceful fallback: Stale cache fallback if provider is down or rate limited
                stale_entry = self._cache.get(cache_key)
                if stale_entry and stale_entry.is_stale_usable():
                    logger.warning(
                        f"Weather provider error ({exc}); serving stale cached weather data for key {cache_key}"
                    )
                    if not inflight_future.done():
                        inflight_future.set_result(stale_entry.data)
                    return stale_entry.data
                else:
                    if not inflight_future.done():
                        inflight_future.set_exception(exc)
                        # Mark exception as retrieved on the future to suppress asyncio GC warnings
                        try:
                            inflight_future.exception()
                        except Exception:
                            pass
                    raise exc

            finally:
                async with self._lock:
                    self._inflight.pop(cache_key, None)
        else:
            # Wait for primary caller's in-flight future
            return await asyncio.shield(inflight_future)

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
