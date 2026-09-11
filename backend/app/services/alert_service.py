"""Deterministic severe weather alert & risk advisory engine.

Rules & Thresholds:
- Thunderstorm Risk (Warning): WMO Weather Codes 95, 96, 99.
- Heavy Rain Risk (Warning): WMO Weather Codes 65, 67, 82 or precipitation >= 15.0 mm.
- Heavy Rain Risk / Watch: precipitation >= 5.0 mm OR (precipitation_probability >= 60% AND precipitation >= 1.0 mm).
- High Wind Risk (Warning): wind_speed >= 60.0 km/h.
- Strong Wind Risk (Watch): wind_speed >= 45.0 km/h.
- Wind Advisory: wind_speed >= 30.0 km/h.
- Extreme Heat Risk (Warning): temperature >= 38.0°C.
- Extreme Cold Risk (Warning): temperature <= 2.0°C.
- Snowfall Risk (Warning): WMO Weather Codes 73, 75, 85, 86.
- Dense Fog Risk (Advisory): WMO Weather Codes 45, 48.

All alerts state strictly grounded factual metrics without speculative emergency instructions.
Titles use 'Risk' / 'Advisory' to avoid implying official government-issued emergency warnings.
"""

import logging
from typing import List
from app.schemas.alert import AlertFactor, WeatherAlert
from app.schemas.query import TargetPeriodWeather

logger = logging.getLogger(__name__)

# Centralized Alert Threshold Constants
HIGH_PRECIP_PROB_ADVISORY = 60  # % rain probability
MIN_PRECIP_FOR_PROB_WATCH = 1.0  # mm precipitation required for prob-based watch
HEAVY_PRECIP_AMOUNT_WATCH = 5.0  # mm precipitation
SEVERE_PRECIP_AMOUNT_WARNING = 15.0  # mm precipitation

HIGH_WIND_ADVISORY = 30.0  # km/h
STRONG_WIND_WATCH = 45.0  # km/h
SEVERE_WIND_WARNING = 60.0  # km/h

EXTREME_HEAT_WARNING = 38.0  # °C
EXTREME_COLD_WARNING = 2.0  # °C

THUNDERSTORM_CODES = [95, 96, 99]
HEAVY_RAIN_CODES = [65, 67, 82]
HEAVY_SNOW_CODES = [73, 75, 85, 86]
FOG_CODES = [45, 48]


class AlertEngineService:
    """Service evaluating real meteorological metrics into grounded severe weather alerts."""

    def evaluate_alerts(
        self,
        period_weather: TargetPeriodWeather,
        location_name: str,
    ) -> List[WeatherAlert]:
        """Evaluate target period weather metrics and return active weather alerts."""
        if not period_weather:
            return []

        alerts: List[WeatherAlert] = []
        pw = period_weather
        loc = location_name.split(',')[0].strip() if location_name else "Selected Location"
        period_str = pw.period_label.replace('_', ' ')

        # 1. Thunderstorm Alert
        if pw.weather_code in THUNDERSTORM_CODES:
            alerts.append(
                WeatherAlert(
                    id=f"alert_thunderstorm_{pw.weather_code}",
                    severity="warning",
                    category="thunderstorm",
                    title=f"Thunderstorm Risk — {loc}",
                    summary=f"Thunderstorm conditions ({pw.condition}) are forecast for {loc} during {period_str}. Exercise caution during lightning.",
                    factors=[
                        AlertFactor(metric="weather_code", value=pw.weather_code, threshold="WMO 95/96/99 Severe Thunderstorm"),
                        AlertFactor(metric="condition", value=pw.condition, threshold="Thunderstorm"),
                        AlertFactor(metric="precipitation_probability", value=f"{pw.precipitation_probability}%", threshold=">40%"),
                    ],
                )
            )

        # 2. Heavy Rain Alert / Warning
        if pw.weather_code in HEAVY_RAIN_CODES or pw.precipitation >= SEVERE_PRECIP_AMOUNT_WARNING:
            alerts.append(
                WeatherAlert(
                    id="alert_heavy_rain_warning",
                    severity="warning",
                    category="heavy_rain",
                    title=f"Heavy Rain Risk — {loc}",
                    summary=f"Heavy rainfall of {pw.precipitation} mm is forecast for {loc} during {period_str}.",
                    factors=[
                        AlertFactor(metric="precipitation", value=f"{pw.precipitation} mm", threshold=f">={SEVERE_PRECIP_AMOUNT_WARNING} mm"),
                        AlertFactor(metric="precipitation_probability", value=f"{pw.precipitation_probability}%", threshold=">=60%"),
                    ],
                )
            )
        elif pw.precipitation >= HEAVY_PRECIP_AMOUNT_WATCH or (
            pw.precipitation_probability >= HIGH_PRECIP_PROB_ADVISORY and pw.precipitation >= MIN_PRECIP_FOR_PROB_WATCH
        ):
            alerts.append(
                WeatherAlert(
                    id="alert_heavy_rain_watch",
                    severity="watch",
                    category="heavy_rain",
                    title=f"Precipitation Risk — {loc}",
                    summary=f"Moderate to heavy rain ({pw.precipitation} mm, {pw.precipitation_probability}% chance) is forecast for {loc} during {period_str}.",
                    factors=[
                        AlertFactor(metric="precipitation_probability", value=f"{pw.precipitation_probability}%", threshold=f">={HIGH_PRECIP_PROB_ADVISORY}%"),
                        AlertFactor(metric="precipitation", value=f"{pw.precipitation} mm", threshold=f">={HEAVY_PRECIP_AMOUNT_WATCH} mm"),
                    ],
                )
            )

        # 3. Wind Speed Alert
        if pw.wind_speed >= SEVERE_WIND_WARNING:
            alerts.append(
                WeatherAlert(
                    id="alert_high_wind_warning",
                    severity="warning",
                    category="high_wind",
                    title=f"High Wind Risk — {loc}",
                    summary=f"High wind speeds reaching {pw.wind_speed} km/h are forecast in {loc} during {period_str}.",
                    factors=[
                        AlertFactor(metric="wind_speed", value=f"{pw.wind_speed} km/h", threshold=f">={SEVERE_WIND_WARNING} km/h"),
                    ],
                )
            )
        elif pw.wind_speed >= STRONG_WIND_WATCH:
            alerts.append(
                WeatherAlert(
                    id="alert_high_wind_watch",
                    severity="watch",
                    category="high_wind",
                    title=f"Strong Wind Risk — {loc}",
                    summary=f"Strong gusty winds reaching {pw.wind_speed} km/h are forecast in {loc} during {period_str}.",
                    factors=[
                        AlertFactor(metric="wind_speed", value=f"{pw.wind_speed} km/h", threshold=f">={STRONG_WIND_WATCH} km/h"),
                    ],
                )
            )
        elif pw.wind_speed >= HIGH_WIND_ADVISORY:
            alerts.append(
                WeatherAlert(
                    id="alert_high_wind_advisory",
                    severity="advisory",
                    category="high_wind",
                    title=f"Elevated Wind Risk — {loc}",
                    summary=f"Breezy conditions with wind speeds of {pw.wind_speed} km/h are forecast in {loc} during {period_str}.",
                    factors=[
                        AlertFactor(metric="wind_speed", value=f"{pw.wind_speed} km/h", threshold=f">={HIGH_WIND_ADVISORY} km/h"),
                    ],
                )
            )

        # 4. Extreme Heat / Extreme Cold
        if pw.temperature >= EXTREME_HEAT_WARNING:
            alerts.append(
                WeatherAlert(
                    id="alert_extreme_heat_warning",
                    severity="warning",
                    category="extreme_heat",
                    title=f"Extreme Heat Risk — {loc}",
                    summary=f"High temperatures reaching {pw.temperature}°C (feels like {pw.feels_like}°C) are forecast for {loc} during {period_str}.",
                    factors=[
                        AlertFactor(metric="temperature", value=f"{pw.temperature}°C", threshold=f">={EXTREME_HEAT_WARNING}°C"),
                        AlertFactor(metric="feels_like", value=f"{pw.feels_like}°C", threshold=f">={EXTREME_HEAT_WARNING}°C"),
                    ],
                )
            )
        elif pw.temperature <= EXTREME_COLD_WARNING:
            alerts.append(
                WeatherAlert(
                    id="alert_extreme_cold_warning",
                    severity="warning",
                    category="extreme_cold",
                    title=f"Extreme Cold Risk — {loc}",
                    summary=f"Freezing temperature of {pw.temperature}°C (feels like {pw.feels_like}°C) is forecast in {loc} during {period_str}.",
                    factors=[
                        AlertFactor(metric="temperature", value=f"{pw.temperature}°C", threshold=f"<={EXTREME_COLD_WARNING}°C"),
                    ],
                )
            )

        # 5. Heavy Snow
        if pw.weather_code in HEAVY_SNOW_CODES:
            alerts.append(
                WeatherAlert(
                    id="alert_heavy_snow_warning",
                    severity="warning",
                    category="heavy_snow",
                    title=f"Snowfall Risk — {loc}",
                    summary=f"Snowfall conditions ({pw.condition}) are forecast in {loc} during {period_str}.",
                    factors=[
                        AlertFactor(metric="weather_code", value=pw.weather_code, threshold="WMO Snowfall"),
                    ],
                )
            )

        # 6. Dense Fog Advisory
        if pw.weather_code in FOG_CODES:
            alerts.append(
                WeatherAlert(
                    id=f"alert_fog_{pw.weather_code}",
                    severity="advisory",
                    category="fog",
                    title=f"Dense Fog Risk — {loc}",
                    summary=f"Fog or freezing fog is forecast in {loc} during {period_str} under {pw.condition} conditions.",
                    factors=[
                        AlertFactor(metric="weather_code", value=pw.weather_code, threshold="WMO 45/48 Fog"),
                        AlertFactor(metric="condition", value=pw.condition, threshold="Fog"),
                    ],
                )
            )

        return alerts


alert_engine_service = AlertEngineService()
