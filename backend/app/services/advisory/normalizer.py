"""Sanitization, date normalization, and taxonomy mapping helpers."""

from datetime import datetime, timezone
import html
import re
from typing import Optional

from app.services.advisory.taxonomy import HazardType, SeverityLevel


def sanitize_text(text: Optional[str]) -> str:
    """Strip HTML tags and unescape text to prevent script injection."""
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = html.unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def parse_datetime(dt_str: Optional[str]) -> datetime:
    """Parse various ISO 8601, RFC 822, or standard date formats to UTC datetime."""
    if not dt_str:
        return datetime.now(timezone.utc)

    cleaned = dt_str.strip()

    iso_formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in iso_formats:
        try:
            s = cleaned.replace("Z", "+00:00")
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue

    return datetime.now(timezone.utc)


def map_hazard_type(event_text: str, description_text: str = "") -> str:
    """Map natural language hazard or event description to controlled HazardType."""
    combined = f"{event_text} {description_text}".lower()

    if any(k in combined for k in ["extremely heavy rain", "extreme rainfall", "very heavy to extremely heavy"]):
        return HazardType.EXTREME_RAIN.value
    if any(k in combined for k in ["very heavy rain", "very heavy rainfall"]):
        return HazardType.VERY_HEAVY_RAIN.value
    if any(k in combined for k in ["heavy rain", "heavy rainfall", "downpour", "torrential"]):
        return HazardType.HEAVY_RAIN.value
    # Check thunderstorm before lightning so composite events map to THUNDERSTORM
    if any(k in combined for k in ["thunderstorm", "kalbaishakhi", "nor'wester"]):
        return HazardType.THUNDERSTORM.value
    if any(k in combined for k in ["lightning", "vajrapath"]):
        return HazardType.LIGHTNING.value
    if any(k in combined for k in ["hail", "hailstorm"]):
        return HazardType.HAIL.value
    if any(k in combined for k in ["cyclone", "cyclonic storm", "depression", "deep depression"]):
        return HazardType.CYCLONE.value
    if any(k in combined for k in ["storm surge"]):
        return HazardType.STORM_SURGE.value
    if any(k in combined for k in ["high wave", "swell surge", "rough sea"]):
        return HazardType.HIGH_WAVE.value
    if any(k in combined for k in ["tsunami"]):
        return HazardType.TSUNAMI.value
    if any(k in combined for k in ["flash flood", "cloudburst"]):
        return HazardType.FLASH_FLOOD.value
    if any(k in combined for k in ["flood", "inundation", "waterlogging"]):
        return HazardType.FLOOD.value
    if any(k in combined for k in ["heatwave", "severe heat wave", "heat wave"]):
        return HazardType.HEATWAVE.value
    if any(k in combined for k in ["cold wave", "severe cold wave", "cold day"]):
        return HazardType.COLD_WAVE.value
    if any(k in combined for k in ["dense fog", "very dense fog", "fog"]):
        return HazardType.FOG.value
    if any(k in combined for k in ["heavy snow", "blizzard", "snowfall"]):
        return HazardType.HEAVY_SNOW.value
    if any(k in combined for k in ["dust storm", "dust raising wind"]):
        return HazardType.DUST_STORM.value
    if any(k in combined for k in ["squall", "gusty wind", "strong wind", "gale"]):
        return HazardType.STRONG_WIND.value
    if any(k in combined for k in ["landslide", "mudslide", "rockfall"]):
        return HazardType.LANDSLIDE.value
    if any(k in combined for k in ["forest fire", "wildfire"]):
        return HazardType.FOREST_FIRE.value
    if any(k in combined for k in ["air quality", "aqi", "smog", "pollution"]):
        return HazardType.AIR_QUALITY.value

    return HazardType.OTHER.value


def map_severity(color_or_level: str) -> str:
    """Map authority severity string, color code, or CAP level to normalized severity using word boundaries."""
    s = color_or_level.lower().strip()

    # 1. Match green / no warning first
    if re.search(r"\b(green|no warning|normal|minor)\b", s):
        return SeverityLevel.GREEN.value

    # 2. Match orange / amber / alert / severe
    if re.search(r"\b(orange|amber|alert|be prepared|severe)\b", s):
        return SeverityLevel.ORANGE.value

    # 3. Match yellow / watch
    if re.search(r"\b(yellow|watch|be updated|moderate)\b", s):
        return SeverityLevel.YELLOW.value

    # 4. Match red / warning / take action / danger / extreme
    if re.search(r"\b(red|warning|take action|danger|extreme)\b", s):
        return SeverityLevel.RED.value

    return SeverityLevel.UNKNOWN.value
