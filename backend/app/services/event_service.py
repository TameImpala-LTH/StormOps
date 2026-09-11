"""Event-Based Environmental Awareness service for deterministic event lookup, status calculation, and environmental pressure advisories."""

from datetime import date, datetime, timedelta
import logging
from typing import List, Optional

from app.schemas.event import EnvironmentalEvent, EnvironmentalPressureItem, EventOccurrence

logger = logging.getLogger(__name__)


# Curated verified 2026 catalogue of major regional environmental events
EVENT_CATALOGUE: List[EnvironmentalEvent] = [
    EnvironmentalEvent(
        id="kolkata-durga-puja-2026",
        title="Durga Puja Festival",
        category="festival",
        geographic_scope=["Kolkata", "West Bengal", "Calcutta"],
        occurrences=[
            EventOccurrence(
                year=2026,
                start_date="2026-10-16",
                end_date="2026-10-21",
                post_event_days=3,
            )
        ],
        environmental_pressures=[
            EnvironmentalPressureItem(type="traffic", level="severe", evidence_type="historical_pattern"),
            EnvironmentalPressureItem(type="noise_pollution", level="high", evidence_type="historical_pattern"),
            EnvironmentalPressureItem(type="congestion", level="severe", evidence_type="historical_pattern"),
            EnvironmentalPressureItem(type="public_activity", level="high", evidence_type="observed"),
        ],
        advisory_summary="Durga Puja brings major public celebrations, large pandal installations, and dense foot traffic across Kolkata. Road diversions and elevated noise levels are typical during peak evening hours.",
        key_recommendations=[
            "Expect road closures and traffic diversions around central pandal zones.",
            "Use Kolkata Metro where possible to bypass major arterial road congestion.",
            "Festival-related activity may remain elevated for several days afterward.",
        ],
        source_metadata="Verified 2026 West Bengal Official Holiday Calendar",
    ),
    EnvironmentalEvent(
        id="mumbai-ganesh-chaturthi-2026",
        title="Ganesh Chaturthi Festival",
        category="festival",
        geographic_scope=["Mumbai", "Maharashtra", "Bombay"],
        occurrences=[
            EventOccurrence(
                year=2026,
                start_date="2026-09-14",
                end_date="2026-09-24",
                post_event_days=3,
            )
        ],
        environmental_pressures=[
            EnvironmentalPressureItem(type="traffic", level="high", evidence_type="historical_pattern"),
            EnvironmentalPressureItem(type="noise_pollution", level="high", evidence_type="historical_pattern"),
            EnvironmentalPressureItem(type="congestion", level="high", evidence_type="observed"),
        ],
        advisory_summary="Ganesh Chaturthi procession rallies and idol immersion days affect vehicular flow along major Mumbai corridors, particularly near coastal immersion routes.",
        key_recommendations=[
            "Plan travel ahead during immersion days (Visarjan) along Girgaon Chowpatty and coastal routes.",
            "Festival-related activity may remain elevated for several days afterward.",
        ],
        source_metadata="Verified 2026 Maharashtra Government Official Holiday List",
    ),
    EnvironmentalEvent(
        id="gujarat-navratri-2026",
        title="Navratri / Garba Celebrations",
        category="festival",
        geographic_scope=["Ahmedabad", "Gujarat", "Vadodara", "Surat", "Rajkot", "Delhi", "New Delhi"],
        occurrences=[
            EventOccurrence(
                year=2026,
                start_date="2026-10-11",
                end_date="2026-10-19",
                post_event_days=2,
            )
        ],
        environmental_pressures=[
            EnvironmentalPressureItem(type="noise_pollution", level="high", evidence_type="historical_pattern"),
            EnvironmentalPressureItem(type="public_activity", level="high", evidence_type="historical_pattern"),
            EnvironmentalPressureItem(type="traffic", level="elevated", evidence_type="historical_pattern"),
        ],
        advisory_summary="Navratri Garba events draw large crowds to open grounds and community venues across Gujarat and major cities. Late-night celebration noise and high foot traffic are characteristic of this nine-night festival.",
        key_recommendations=[
            "Expect elevated noise levels near Garba venues during evening and night hours.",
            "Traffic around major celebration grounds can be significantly congested after dark.",
            "Plan outdoor activities or early-morning travel to avoid peak crowd periods.",
        ],
        source_metadata="Verified 2026 Shardiya Navratri dates — multiple corroborated Hindu Panchang sources (devaastha.com, nkbmeditation.org, panditsnearme.com)",
    ),
    EnvironmentalEvent(
        id="mumbai-diwali-2026",
        title="Diwali Celebrations",
        category="festival",
        geographic_scope=["Mumbai", "Maharashtra", "Bombay"],
        occurrences=[
            EventOccurrence(
                year=2026,
                start_date="2026-11-08",
                end_date="2026-11-12",
                post_event_days=3,
            )
        ],
        environmental_pressures=[
            EnvironmentalPressureItem(type="air_pollution", level="elevated", evidence_type="historical_pattern"),
            EnvironmentalPressureItem(type="noise_pollution", level="high", evidence_type="historical_pattern"),
            EnvironmentalPressureItem(type="traffic", level="elevated", evidence_type="historical_pattern"),
        ],
        advisory_summary="Diwali festive lighting and pyrotechnics temporarily increase evening smoke, noise, and commercial market foot traffic across Mumbai.",
        key_recommendations=[
            "Sensitive individuals should consider wearing protective masks during peak evening smoke hours.",
            "Festival-related activity may remain elevated for several days afterward.",
        ],
        source_metadata="Verified 2026 Official Holiday Calendar",
    ),
    EnvironmentalEvent(
        id="delhi-diwali-2026",
        title="Diwali Celebrations",
        category="festival",
        geographic_scope=["Delhi", "New Delhi", "NCR", "Noida", "Gurugram", "Gurgaon", "Faridabad", "Ghaziabad"],
        occurrences=[
            EventOccurrence(
                year=2026,
                start_date="2026-11-08",
                end_date="2026-11-12",
                post_event_days=3,
            )
        ],
        environmental_pressures=[
            EnvironmentalPressureItem(type="air_pollution", level="severe", evidence_type="historical_pattern"),
            EnvironmentalPressureItem(type="noise_pollution", level="high", evidence_type="historical_pattern"),
            EnvironmentalPressureItem(type="traffic", level="high", evidence_type="historical_pattern"),
        ],
        advisory_summary="Diwali celebrations combined with autumn atmospheric stagnation historically result in dense evening smoke, particulate accumulation, and shopping market traffic across the National Capital Region.",
        key_recommendations=[
            "Use N95 masks during outdoor evening activities if smoke accumulation is visible.",
            "Festival-related activity may remain elevated for several days afterward.",
        ],
        source_metadata="Verified 2026 Delhi Government Official Holiday Calendar",
    ),
    EnvironmentalEvent(
        id="kolkata-chhath-puja-2026",
        title="Chhath Puja",
        category="festival",
        geographic_scope=["Kolkata", "West Bengal", "Bihar", "Jharkhand", "Patna", "Ranchi"],
        occurrences=[
            EventOccurrence(
                year=2026,
                start_date="2026-11-13",
                end_date="2026-11-16",
                post_event_days=2,
            )
        ],
        environmental_pressures=[
            EnvironmentalPressureItem(type="traffic", level="high", evidence_type="historical_pattern"),
            EnvironmentalPressureItem(type="public_activity", level="high", evidence_type="historical_pattern"),
            EnvironmentalPressureItem(type="congestion", level="high", evidence_type="historical_pattern"),
        ],
        advisory_summary="Chhath Puja draws large crowds to riverbanks and water bodies for sunrise and sunset Arghya rituals. Routes to major ghats experience significant congestion, particularly on Sandhya Arghya and Usha Arghya days.",
        key_recommendations=[
            "Plan travel well in advance on Nov 15–16 (Sandhya and Usha Arghya days) near riverside ghats.",
            "Expect road diversions and heavy foot traffic along major ghat access routes.",
            "Early morning departures on Nov 16 (Usha Arghya) are particularly affected near waterfronts.",
        ],
        source_metadata="Verified 2026 Chhath Puja dates — multiple corroborated sources (divinehindu.in, manyavar.com, samvat.in, caclubindia.com)",
    ),
]


class EventService:
    """Service providing deterministic event matching and environmental advisories."""

    def __init__(self, catalogue: Optional[List[EnvironmentalEvent]] = None):
        self.catalogue = catalogue if catalogue is not None else EVENT_CATALOGUE

    def get_location_events(
        self,
        location_name: str,
        target_date: Optional[date] = None,
        visibility_window_days: int = 60,
    ) -> List[EnvironmentalEvent]:
        """Return list of matching environmental events for a location and target date,
        sorted: active first, then upcoming (soonest first), then post_event."""
        if not location_name:
            return []

        # Phase 10B fix: use real date.today() as the fallback — never a hardcoded date.
        ref_date = target_date if target_date is not None else date.today()
        target_loc = location_name.lower().strip()

        matched_events: List[EnvironmentalEvent] = []

        for event in self.catalogue:
            # Geographic scope matching
            geo_match = any(
                scope.lower() in target_loc or target_loc in scope.lower()
                for scope in event.geographic_scope
            )
            if not geo_match:
                continue

            # Check occurrences for matching year / date window
            for occ in event.occurrences:
                start_d = datetime.strptime(occ.start_date, "%Y-%m-%d").date()
                end_d = datetime.strptime(occ.end_date, "%Y-%m-%d").date()
                post_end_d = end_d + timedelta(days=occ.post_event_days)
                earliest_visible = start_d - timedelta(days=visibility_window_days)

                status: Optional[str] = None
                days_until: Optional[int] = None

                if start_d <= ref_date <= end_d:
                    status = "active"
                    days_until = 0
                elif end_d < ref_date <= post_end_d:
                    status = "post_event"
                    days_until = 0
                elif earliest_visible <= ref_date < start_d:
                    status = "upcoming"
                    days_until = (start_d - ref_date).days

                if status in ["upcoming", "active", "post_event"]:
                    # Create a fresh model instance with computed status & days_until
                    event_copy = event.model_copy(deep=True)
                    event_copy.status = status
                    event_copy.days_until = days_until
                    matched_events.append(event_copy)

        # Phase 10B: Sort deterministically — active first, upcoming soonest-first, post_event last.
        def _sort_key(e: EnvironmentalEvent) -> tuple:
            if e.status == "active":
                return (0, 0)
            elif e.status == "upcoming":
                return (1, e.days_until or 0)
            else:  # post_event
                return (2, 0)

        matched_events.sort(key=_sort_key)
        return matched_events


event_service = EventService()
