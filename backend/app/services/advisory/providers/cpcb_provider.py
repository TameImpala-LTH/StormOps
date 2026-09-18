"""Central Pollution Control Board (CPCB) air quality provider adapter."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from app.services.advisory.base import BaseAdvisoryProvider
from app.services.advisory.models import NormalizedAdvisory
from app.services.advisory.normalizer import parse_datetime, sanitize_text
from app.services.advisory.taxonomy import Authority, Granularity, HazardType, SeverityLevel

logger = logging.getLogger(__name__)


class CpcbAqiProvider(BaseAdvisoryProvider):
    """Provider adapter for CPCB National Air Quality Index (NAQI) bulletins.

    Maintains complete product separation: AQI is classified as AIR_QUALITY
    and never conflated with atmospheric IMD meteorological color warnings.
    """

    @property
    def authority(self) -> str:
        return Authority.CPCB.value

    @property
    def name(self) -> str:
        return "CPCB Central Control Room for Air Quality"

    async def fetch_raw(self) -> Optional[Dict[str, Any]]:
        # Dedicated CPCB CAAQM endpoint integration hook
        return None

    def parse_payload(self, raw_data: Any) -> List[NormalizedAdvisory]:
        if not raw_data or not isinstance(raw_data, list):
            return []

        advisories: List[NormalizedAdvisory] = []
        for station in raw_data:
            try:
                advisory = self._parse_station_aqi(station)
                if advisory:
                    advisories.append(advisory)
            except Exception as e:
                logger.debug(f"Skipping malformed CPCB station item: {e}")

        return advisories

    def _parse_station_aqi(self, data: Dict[str, Any]) -> Optional[NormalizedAdvisory]:
        aqi_val = data.get("aqi")
        if aqi_val is None:
            return None

        city = data.get("city") or "Urban Center"
        state = data.get("state")
        station_name = data.get("station_name") or city
        prominent_pollutant = data.get("prominent_pollutant") or "PM2.5"

        # Determine official NAQI category and mapped severity
        if aqi_val <= 50:
            category = "Good"
            severity = SeverityLevel.GREEN.value
        elif aqi_val <= 100:
            category = "Satisfactory"
            severity = SeverityLevel.GREEN.value
        elif aqi_val <= 200:
            category = "Moderate"
            severity = SeverityLevel.YELLOW.value
        elif aqi_val <= 300:
            category = "Poor"
            severity = SeverityLevel.ORANGE.value
        elif aqi_val <= 400:
            category = "Very Poor"
            severity = SeverityLevel.RED.value
        else:
            category = "Severe"
            severity = SeverityLevel.RED.value

        now_utc = datetime.now(timezone.utc)
        source_id = f"cpcb-{city.lower()}-{now_utc.strftime('%Y%m%d%H')}"

        return NormalizedAdvisory(
            source_id=source_id,
            authority=Authority.CPCB.value,
            hazard_type=HazardType.AIR_QUALITY.value,
            severity=severity,
            official_level=f"AQI {aqi_val} ({category})",
            urgency="immediate" if aqi_val > 200 else "expected",
            certainty="observed",
            issued_at=now_utc,
            effective_at=now_utc,
            expires_at=datetime.fromtimestamp(now_utc.timestamp() + 14400, tz=timezone.utc),  # 4-hour window
            granularity=Granularity.STATION.value,
            state=state,
            district=city,
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            headline=f"CPCB Air Quality: {city} is {category} (AQI {aqi_val})",
            description=sanitize_text(f"Station: {station_name}. Prominent pollutant is {prominent_pollutant}."),
            action_guidance=self._get_health_guidance(category),
            source_url="https://app.cpcbccr.com/ccr/",
            raw_payload=data,
        )

    def _get_health_guidance(self, category: str) -> str:
        guidance = {
            "Good": "Minimal impact on health. Outdoor activities are safe.",
            "Satisfactory": "Minor breathing discomfort to sensitive individuals.",
            "Moderate": "Breathing discomfort to people with lung, asthma, and heart conditions.",
            "Poor": "Breathing discomfort to most people on prolonged outdoor exposure.",
            "Very Poor": "Respiratory illness on prolonged exposure. Sensitive groups should stay indoors.",
            "Severe": "Affects healthy individuals and seriously impacts those with existing conditions.",
        }
        return guidance.get(category, "Monitor real-time air quality updates.")
