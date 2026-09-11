"""Environmental Outlook router for authenticated users.

Exposes deterministic environmental periods across the user's saved locations
and current location, reusing the verified EventService catalogue without duplicating
data in PostgreSQL or introducing forecasting/AQI prediction.
"""

from typing import List, Optional, Set
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.saved_location import SavedLocation
from app.models.user import User
from app.schemas.outlook import EnvironmentalOutlookItem, EnvironmentalOutlookResponse
from app.services.event_service import event_service

router = APIRouter()


@router.get("/outlook", response_model=EnvironmentalOutlookResponse)
def get_environmental_outlook(
    current_location: Optional[str] = Query(
        None,
        description="Optional human-readable name of currently viewed location",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve deterministic upcoming or active environmental periods across the authenticated user's locations.

    Strictly scopes saved location queries to current_user.id.
    Uses EventService as the sole source of truth.
    Returns deterministic, evidence-based outlook without predictive claims.
    """
    # 1. Fetch user's saved locations (strictly scoped to current_user.id)
    saved_locations = (
        db.query(SavedLocation)
        .filter(SavedLocation.user_id == current_user.id)
        .order_by(SavedLocation.created_at.desc())
        .all()
    )

    # 2. Build list of unique location names to evaluate
    locations_evaluated: List[str] = []
    seen_locs: Set[str] = set()

    # If current_location was provided, evaluate it first
    if current_location and current_location.strip():
        loc_clean = current_location.strip()
        locations_evaluated.append(loc_clean)
        seen_locs.add(loc_clean.lower())

    for sl in saved_locations:
        loc_name = sl.name.strip()
        if loc_name.lower() not in seen_locs:
            locations_evaluated.append(loc_name)
            seen_locs.add(loc_name.lower())

    # 3. For each location, query EventService
    outlook_items: List[EnvironmentalOutlookItem] = []
    seen_event_location_pairs: Set[str] = set()

    for loc in locations_evaluated:
        events = event_service.get_location_events(loc)
        for evt in events:
            pair_key = f"{evt.id}:{loc.lower()}"
            if pair_key in seen_event_location_pairs:
                continue
            seen_event_location_pairs.add(pair_key)

            # Extract occurrence dates
            start_d = None
            end_d = None
            post_days = 3
            if evt.occurrences:
                occ = evt.occurrences[0]
                start_d = occ.start_date
                end_d = occ.end_date
                post_days = occ.post_event_days

            outlook_items.append(
                EnvironmentalOutlookItem(
                    event_id=evt.id,
                    event_title=evt.title,
                    category=evt.category,
                    location_name=loc,
                    start_date=start_d or "",
                    end_date=end_d,
                    post_event_days=post_days,
                    status=evt.status or "upcoming",
                    days_until=evt.days_until,
                    advisory_summary=evt.advisory_summary,
                    evidence_note="Historically associated with increased local environmental pressure.",
                    environmental_pressures=evt.environmental_pressures,
                    key_recommendations=evt.key_recommendations,
                    source_metadata=evt.source_metadata,
                )
            )

    # 4. Sort deterministically:
    # 1) active events first
    # 2) upcoming events by nearest start date / days_until ascending
    # 3) post_event last
    def _outlook_sort_key(item: EnvironmentalOutlookItem) -> tuple:
        if item.status == "active":
            return (0, 0, item.start_date)
        elif item.status == "upcoming":
            return (1, item.days_until if item.days_until is not None else 9999, item.start_date)
        else:
            return (2, 0, item.start_date)

    outlook_items.sort(key=_outlook_sort_key)

    return EnvironmentalOutlookResponse(
        items=outlook_items,
        total_events=len(outlook_items),
        locations_evaluated=locations_evaluated,
    )
