"""Advisory query and resolution service for StormOps.

Provides hierarchical location matching (point/nowcast -> district -> subdivision -> state),
severity ranking, in-memory caching, and seamless query resolution.
"""

from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.advisory import Advisory
from app.schemas.advisory import AdvisoryQueryFilter, AdvisoryResponse

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {
    "red": 4,
    "orange": 3,
    "yellow": 2,
    "green": 1,
    "unknown": 0,
}


class AdvisoryService:
    """Service providing fast advisory lookups, hierarchical spatial resolution, and caching."""

    def __init__(self):
        self._district_cache: Dict[str, List[AdvisoryResponse]] = {}
        self._state_cache: Dict[str, List[AdvisoryResponse]] = {}
        self._last_cache_refresh: Optional[datetime] = None

    def get_advisories(
        self,
        db: Session,
        filter_params: AdvisoryQueryFilter,
    ) -> List[AdvisoryResponse]:
        """Query advisories matching location filter, ranked by severity and recency."""
        now_utc = datetime.now(timezone.utc)
        query = db.query(Advisory)

        if not filter_params.include_expired:
            query = query.filter(
                Advisory.expires_at > now_utc,
            )

        if filter_params.authority:
            query = query.filter(Advisory.authority == filter_params.authority.upper())

        if filter_params.hazard_type:
            query = query.filter(Advisory.hazard_type == filter_params.hazard_type.upper())

        if filter_params.severity:
            query = query.filter(Advisory.severity == filter_params.severity.lower())

        records = query.all()
        responses = [AdvisoryResponse.model_validate(r) for r in records]

        # Filter geographically if location parameters provided
        matched_items = self._match_geography(
            responses,
            district=filter_params.district,
            state=filter_params.state,
            subdivision=filter_params.subdivision,
            lat=filter_params.latitude,
            lon=filter_params.longitude,
        )

        # Sort: Highest severity first, then geographic precedence (point > district > subdivision > state > national), then latest issued_at
        matched_items.sort(
            key=lambda item: (
                SEVERITY_ORDER.get(item[0].severity.lower(), 0),
                item[1],
                item[0].issued_at.timestamp() if item[0].issued_at else 0,
            ),
            reverse=True,
        )

        return [adv for adv, _ in matched_items]

    def _match_geography(
        self,
        advisories: List[AdvisoryResponse],
        district: Optional[str] = None,
        state: Optional[str] = None,
        subdivision: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> List[tuple]:
        """Hierarchically match advisories to query location and assign geographic precedence tier."""
        if not (district or state or subdivision or (lat is not None and lon is not None)):
            return [(adv, 0) for adv in advisories]

        dist_clean = district.lower().strip() if district else ""
        state_clean = state.lower().strip() if state else ""
        sub_clean = subdivision.lower().strip() if subdivision else ""

        matched: List[tuple] = []
        for adv in advisories:
            adv_dist = (adv.district or "").lower().strip()
            adv_state = (adv.state or "").lower().strip()
            adv_sub = (adv.subdivision or "").lower().strip()

            # 1. Point / Coordinates radius match (Tier 5)
            if lat is not None and lon is not None and adv.latitude is not None and adv.longitude is not None:
                radius_km = adv.radius_km or 25.0
                deg_dist = ((adv.latitude - lat) ** 2 + (adv.longitude - lon) ** 2) ** 0.5
                if deg_dist * 111.0 <= radius_km:
                    matched.append((adv, 5))
                    continue

            # 2. District exact or substring match (Tier 4)
            if dist_clean and adv_dist and (dist_clean in adv_dist or adv_dist in dist_clean):
                matched.append((adv, 4))
                continue

            # 3. Subdivision match (Tier 3)
            if sub_clean and adv_sub and (sub_clean in adv_sub or adv_sub in sub_clean):
                matched.append((adv, 3))
                continue

            # 4. State level match (Tier 2)
            if state_clean and adv_state and (state_clean in adv_state or adv_state in state_clean):
                matched.append((adv, 2))
                continue

            # 5. National level match (Tier 1: national granularity or pan-India scope)
            if adv.granularity == "national" or (not adv_dist and not adv_state and not adv_sub and adv.latitude is None):
                matched.append((adv, 1))
                continue

        return matched


advisory_service = AdvisoryService()
