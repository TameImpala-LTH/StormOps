"""Controlled internal hazard taxonomy and severity definitions for StormOps."""

from enum import Enum


class HazardType(str, Enum):
    """Normalized hazard classifications covering hydrometeorological and environmental events."""

    HEAVY_RAIN = "HEAVY_RAIN"
    VERY_HEAVY_RAIN = "VERY_HEAVY_RAIN"
    EXTREME_RAIN = "EXTREME_RAIN"
    THUNDERSTORM = "THUNDERSTORM"
    LIGHTNING = "LIGHTNING"
    HAIL = "HAIL"
    STRONG_WIND = "STRONG_WIND"
    DUST_STORM = "DUST_STORM"
    HEATWAVE = "HEATWAVE"
    COLD_WAVE = "COLD_WAVE"
    FOG = "FOG"
    HEAVY_SNOW = "HEAVY_SNOW"
    CYCLONE = "CYCLONE"
    FLOOD = "FLOOD"
    FLASH_FLOOD = "FLASH_FLOOD"
    STORM_SURGE = "STORM_SURGE"
    HIGH_WAVE = "HIGH_WAVE"
    TSUNAMI = "TSUNAMI"
    LANDSLIDE = "LANDSLIDE"
    FOREST_FIRE = "FOREST_FIRE"
    AIR_QUALITY = "AIR_QUALITY"
    OTHER = "OTHER"


class SeverityLevel(str, Enum):
    """Normalized warning severity levels."""

    GREEN = "green"          # No warning / Normal
    YELLOW = "yellow"        # Watch / Be updated
    ORANGE = "orange"        # Alert / Be prepared
    RED = "red"              # Warning / Take action
    UNKNOWN = "unknown"


class Authority(str, Enum):
    """Official government issuing authority."""

    IMD = "IMD"              # India Meteorological Department
    NDMA = "NDMA"            # National Disaster Management Authority (SACHET)
    CWC = "CWC"              # Central Water Commission
    INCOIS = "INCOIS"        # Indian National Centre for Ocean Information Services
    GSI = "GSI"              # Geological Survey of India
    FSI = "FSI"              # Forest Survey of India
    CPCB = "CPCB"            # Central Pollution Control Board
    SDMA = "SDMA"            # State Disaster Management Authority
    OTHER = "OTHER"


class Granularity(str, Enum):
    """Geographic granularity of advisory distribution."""

    STATION = "station"
    NOWCAST = "nowcast"
    DISTRICT = "district"
    SUBDIVISION = "subdivision"
    STATE = "state"
    NATIONAL = "national"
