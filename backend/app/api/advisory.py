"""API router for official environmental and meteorological advisories."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import verify_ingest_token
from app.db.session import get_db
from app.schemas.advisory import AdvisoryListResponse, AdvisoryQueryFilter
from app.services.advisory.ingestion import advisory_ingestion_service
from app.services.advisory_service import advisory_service

router = APIRouter()


@router.get("/advisories", response_model=AdvisoryListResponse)
def get_location_advisories(
    district: Optional[str] = Query(None, description="Target district name (e.g. Kolkata, Mumbai)"),
    state: Optional[str] = Query(None, description="Target state or UT name (e.g. West Bengal)"),
    subdivision: Optional[str] = Query(None, description="IMD meteorological subdivision name"),
    latitude: Optional[float] = Query(None, description="Latitude for spatial radius matching"),
    longitude: Optional[float] = Query(None, description="Longitude for spatial radius matching"),
    authority: Optional[str] = Query(None, description="Filter by authority: IMD, NDMA, CWC, INCOIS, CPCB"),
    hazard_type: Optional[str] = Query(None, description="Filter by hazard type: HEAVY_RAIN, HEATWAVE, etc."),
    severity: Optional[str] = Query(None, description="Filter by severity: red, orange, yellow, green"),
    include_expired: bool = Query(False, description="Whether to include expired historical advisories"),
    db: Session = Depends(get_db),
):
    """Retrieve normalized active hazard advisories for a location."""
    filters = AdvisoryQueryFilter(
        district=district,
        state=state,
        subdivision=subdivision,
        latitude=latitude,
        longitude=longitude,
        authority=authority,
        hazard_type=hazard_type,
        severity=severity,
        include_expired=include_expired,
    )

    advisories = advisory_service.get_advisories(db=db, filter_params=filters)

    return AdvisoryListResponse(
        total=len(advisories),
        advisories=advisories,
        district=district,
        state=state,
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/advisories/ingest", tags=["advisories-admin"])
async def trigger_advisory_ingestion(
    authorized: bool = Depends(verify_ingest_token),
    db: Session = Depends(get_db),
):
    """Trigger an on-demand ingestion cycle across all configured official providers.

    Protected endpoint: Requires Authorization Bearer token or X-Ingest-Key header matching
    the configured ingestion secret or a valid authenticated user JWT.
    """
    result = await advisory_ingestion_service.ingest_all(db=db)
    return {
        "status": "success",
        "result": result,
    }
