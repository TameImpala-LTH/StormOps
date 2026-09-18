"""India Meteorological Department (IMD) warning provider adapter."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
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


class ImdDistrictProvider(BaseAdvisoryProvider):
    """Provider for IMD District-Level Weather Warnings and Radar Nowcasts."""

    @property
    def authority(self) -> str:
        return Authority.IMD.value

    @property
    def name(self) -> str:
        return "IMD District Warning & Nowcast Service"

    async def fetch_raw(self) -> Optional[Dict[str, Any]]:
        """Fetch warning data from IMD endpoints if configured, or gracefully return None."""
        base_url = settings.advisory_imd_api_url
        if not base_url:
            return None

        headers = {"User-Agent": "StormOps-Intelligence/1.0"}
        if settings.advisory_imd_api_key:
            headers["Authorization"] = f"Bearer {settings.advisory_imd_api_key}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{base_url}/warnings/district", headers=headers)
                if resp.status_code == 200:
                    return resp.json()
                logger.info(f"IMD endpoint returned status {resp.status_code}; continuing with graceful degradation")
                return None
        except Exception as e:
            logger.info(f"IMD direct API unreachable ({e}); falling back to SACHET/cache")
            return None

    def parse_payload(self, raw_data: Any) -> List[NormalizedAdvisory]:
        """Parse IMD JSON district warning payload."""
        if not raw_data or not isinstance(raw_data, dict):
            return []

        advisories: List[NormalizedAdvisory] = []
        items = raw_data.get("data") or raw_data.get("warnings") or []

        for item in items:
            try:
                advisory = self._parse_item(item)
                if advisory:
                    advisories.append(advisory)
            except Exception as e:
                logger.debug(f"Skipping malformed IMD item: {e}")

        return advisories

    def _parse_item(self, item: Dict[str, Any]) -> Optional[NormalizedAdvisory]:
        district = item.get("district_name") or item.get("district")
        state = item.get("state_name") or item.get("state")
        subdivision = item.get("subdivision_name") or item.get("subdivision")

        # Warning color / severity code
        raw_color = item.get("warning_color") or item.get("colour_code") or item.get("color") or "GREEN"
        severity = map_severity(raw_color)

        # Skip green normal bulletins if requested to keep DB focused on active warnings
        warning_text = item.get("warning_text") or item.get("description") or ""
        headline = item.get("headline") or f"IMD {raw_color.upper()} Warning: {district or state}"

        issued_at = parse_datetime(item.get("issued_at") or item.get("date"))
        effective_at = parse_datetime(item.get("valid_from") or item.get("from_date"))
        expires_at = parse_datetime(item.get("valid_to") or item.get("to_date"))

        # Default 24h validity window if missing
        if expires_at <= effective_at:
            expires_at = datetime.fromtimestamp(effective_at.timestamp() + 86400, tz=timezone.utc)

        hazard_type = map_hazard_type(item.get("hazard_type", ""), warning_text)
        source_id = str(item.get("id") or f"imd-{district}-{int(effective_at.timestamp())}")

        return NormalizedAdvisory(
            source_id=source_id,
            authority=Authority.IMD.value,
            hazard_type=hazard_type,
            severity=severity,
            official_level=f"IMD {raw_color.capitalize()}",
            urgency="expected",
            certainty="likely",
            issued_at=issued_at,
            effective_at=effective_at,
            expires_at=expires_at,
            granularity=Granularity.DISTRICT.value if district else Granularity.SUBDIVISION.value,
            state=state,
            district=district,
            subdivision=subdivision,
            headline=sanitize_text(headline),
            description=sanitize_text(warning_text) or headline,
            action_guidance=sanitize_text(item.get("action_advice", "")),
            source_url="https://mausam.imd.gov.in",
            raw_payload=item,
        )
