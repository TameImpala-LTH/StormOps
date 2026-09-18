"""NDMA SACHET Common Alerting Protocol (CAP v1.2) provider adapter."""

from datetime import datetime, timezone
import logging
from typing import Any, List, Optional
import xml.etree.ElementTree as ET

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


class SachetCapProvider(BaseAdvisoryProvider):
    """Provider for NDMA SACHET national CAP (OASIS CAP v1.2 / ITU-T X.1303) feeds."""

    @property
    def authority(self) -> str:
        return Authority.NDMA.value

    @property
    def name(self) -> str:
        return "NDMA SACHET CAP Feed"

    async def fetch_raw(self) -> Optional[str]:
        """Fetch active alerts feed from NDMA SACHET portal."""
        url = settings.advisory_sachet_feed_url
        if not url:
            return None

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers={"User-Agent": "StormOps-Intelligence/1.0"})
            if response.status_code == 200:
                return response.text
            logger.warning(f"SACHET feed returned status {response.status_code}")
            return None

    def parse_payload(self, raw_data: str) -> List[NormalizedAdvisory]:
        """Safely parse CAP XML (or RSS containing CAP items) into NormalizedAdvisory items."""
        if not raw_data or not raw_data.strip():
            return []

        advisories: List[NormalizedAdvisory] = []
        try:
            # Safe XML parse
            root = ET.fromstring(raw_data)
        except Exception as e:
            logger.warning(f"XML parse error in SACHET payload: {e}")
            return []

        # Handle XML namespace if present
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        # Determine if root is an <alert> or an <rss>/<feed> containing items
        alert_elements = []
        if root.tag.endswith("alert"):
            alert_elements.append(root)
        else:
            for el in root.iter():
                if el.tag.endswith("alert") or el.tag.endswith("item"):
                    alert_elements.append(el)

        for alert in alert_elements:
            try:
                advisory = self._parse_single_alert(alert, ns)
                if advisory:
                    advisories.append(advisory)
            except Exception as item_err:
                logger.debug(f"Skipping malformed alert element: {item_err}")

        return advisories

    def _parse_single_alert(self, alert_el: ET.Element, ns: str) -> Optional[NormalizedAdvisory]:
        """Parse individual CAP <alert> or RSS <item>."""
        def _get_text(tag_name: str, parent: ET.Element = alert_el) -> str:
            # Try with namespace then without
            node = parent.find(f"{ns}{tag_name}")
            if node is None:
                node = parent.find(tag_name)
            return node.text.strip() if node is not None and node.text else ""

        identifier = _get_text("identifier") or _get_text("guid") or f"sachet-{int(datetime.now(timezone.utc).timestamp())}"
        sender = _get_text("sender") or "NDMA"
        sent_str = _get_text("sent") or _get_text("pubDate")
        issued_at = parse_datetime(sent_str)

        # Locate <info> block
        info_el = alert_el.find(f"{ns}info")
        if info_el is None:
            info_el = alert_el.find("info")
        if info_el is None:
            info_el = alert_el

        event = _get_text("event", info_el) or _get_text("title", alert_el) or "Hazard Warning"
        urgency = _get_text("urgency", info_el).lower() or "expected"
        raw_severity = _get_text("severity", info_el) or "Moderate"
        certainty = _get_text("certainty", info_el).lower() or "likely"

        effective_str = _get_text("effective", info_el)
        expires_str = _get_text("expires", info_el)

        effective_at = parse_datetime(effective_str) if effective_str else issued_at
        # Default expiry to 24h if missing
        if expires_str:
            expires_at = parse_datetime(expires_str)
        else:
            expires_at = datetime.fromtimestamp(effective_at.timestamp() + 86400, tz=timezone.utc)

        headline = sanitize_text(_get_text("headline", info_el) or _get_text("title", alert_el))
        description = sanitize_text(_get_text("description", info_el))
        instruction = sanitize_text(_get_text("instruction", info_el))

        # Spatial parsing from <area>
        area_el = info_el.find(f"{ns}area")
        if area_el is None:
            area_el = info_el.find("area")
        area_desc = ""
        latitude = None
        longitude = None
        radius_km = None
        polygon_geojson = None

        if area_el is not None:
            area_desc = _get_text("areaDesc", area_el)
            circle_str = _get_text("circle", area_el)
            if circle_str and " " in circle_str:
                parts = circle_str.split()
                if len(parts) >= 2:
                    coords, rad = parts[0], parts[1]
                    lat_lng = coords.split(",")
                    if len(lat_lng) == 2:
                        latitude = float(lat_lng[0])
                        longitude = float(lat_lng[1])
                        radius_km = float(rad)

            poly_str = _get_text("polygon", area_el)
            if poly_str:
                polygon_geojson = poly_str

        # Derive state and district from area_desc if available
        state = None
        district = None
        if area_desc:
            parts = [p.strip() for p in area_desc.split(",") if p.strip()]
            if len(parts) >= 2:
                district = parts[0]
                state = parts[1]
            elif len(parts) == 1:
                district = parts[0]

        hazard_type = map_hazard_type(event, description)
        severity = map_severity(raw_severity)

        return NormalizedAdvisory(
            source_id=identifier,
            authority=Authority.NDMA.value if "ndma" in sender.lower() else Authority.IMD.value,
            hazard_type=hazard_type,
            severity=severity,
            official_level=raw_severity,
            urgency=urgency,
            certainty=certainty,
            issued_at=issued_at,
            effective_at=effective_at,
            expires_at=expires_at,
            granularity=Granularity.DISTRICT.value if district else Granularity.STATE.value,
            state=state,
            district=district,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            polygon_geojson=polygon_geojson,
            headline=headline or f"{raw_severity.upper()}: {event}",
            description=description or headline,
            action_guidance=instruction or None,
            source_url=_get_text("web", info_el) or _get_text("link", alert_el) or "https://sachet.ndma.gov.in",
            raw_payload={"sender": sender, "event": event, "raw_severity": raw_severity},
        )
