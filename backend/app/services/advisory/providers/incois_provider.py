"""Indian National Centre for Ocean Information Services (INCOIS) provider adapter."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from app.services.advisory.base import BaseAdvisoryProvider
from app.services.advisory.models import NormalizedAdvisory
from app.services.advisory.normalizer import (
    map_hazard_type,
    map_severity,
    parse_datetime,
    sanitize_text,
)
from app.services.advisory.taxonomy import Authority, Granularity

logger = logging.getLogger(__name__)


class IncoisMarineProvider(BaseAdvisoryProvider):
    """Provider adapter for INCOIS High Wave, Swell Surge, and Ocean State Alerts."""

    @property
    def authority(self) -> str:
        return Authority.INCOIS.value

    @property
    def name(self) -> str:
        return "INCOIS Ocean State & Wave Warning System"

    async def fetch_raw(self) -> Optional[Dict[str, Any]]:
        # Dedicated INCOIS endpoint integration hook
        return None

    def parse_payload(self, raw_data: Any) -> List[NormalizedAdvisory]:
        if not raw_data or not isinstance(raw_data, list):
            return []

        advisories: List[NormalizedAdvisory] = []
        for item in raw_data:
            try:
                alert = self._parse_marine_alert(item)
                if alert:
                    advisories.append(alert)
            except Exception as e:
                logger.debug(f"Skipping malformed INCOIS alert: {e}")

        return advisories

    def _parse_marine_alert(self, item: Dict[str, Any]) -> Optional[NormalizedAdvisory]:
        coastal_stretch = item.get("coast") or item.get("state") or "Coastal India"
        wave_height = item.get("max_wave_height_meters")
        alert_type = item.get("alert_type") or "High Wave Alert"

        issued_at = parse_datetime(item.get("issued_at"))
        expires_at = parse_datetime(item.get("expires_at"))

        hazard_type = map_hazard_type(alert_type, f"Wave height: {wave_height}m")
        severity = map_severity(item.get("severity") or "orange")

        source_id = str(item.get("alert_id") or f"incois-{coastal_stretch}-{int(issued_at.timestamp())}")

        return NormalizedAdvisory(
            source_id=source_id,
            authority=Authority.INCOIS.value,
            hazard_type=hazard_type,
            severity=severity,
            official_level=alert_type,
            urgency="expected",
            certainty="observed",
            issued_at=issued_at,
            effective_at=issued_at,
            expires_at=expires_at,
            granularity=Granularity.STATE.value,
            state=coastal_stretch,
            headline=f"INCOIS: {alert_type} along {coastal_stretch}",
            description=sanitize_text(item.get("description", f"Waves up to {wave_height}m forecasted.")),
            action_guidance=sanitize_text(item.get("fishermen_advisory", "Fishermen are advised not to venture into rough sea.")),
            source_url="https://incois.gov.in",
            raw_payload=item,
        )
