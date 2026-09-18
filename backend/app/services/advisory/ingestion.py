"""Advisory ingestion and deduplication service."""

import asyncio
from datetime import datetime, timezone
import logging
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.advisory import Advisory
from app.services.advisory.base import BaseAdvisoryProvider
from app.services.advisory.models import NormalizedAdvisory
from app.services.advisory.providers.sachet_provider import SachetCapProvider
from app.services.advisory.providers.imd_provider import ImdDistrictProvider
from app.services.advisory.providers.incois_provider import IncoisMarineProvider
from app.services.advisory.providers.cpcb_provider import CpcbAqiProvider

logger = logging.getLogger(__name__)


class AdvisoryIngestionService:
    """Orchestrates multi-source advisory ingestion, deduplication, and database persistence."""

    def __init__(self, providers: Optional[List[BaseAdvisoryProvider]] = None):
        self.providers: List[BaseAdvisoryProvider] = providers or [
            SachetCapProvider(),
            ImdDistrictProvider(),
            IncoisMarineProvider(),
            CpcbAqiProvider(),
        ]

    async def ingest_all(self, db: Session) -> dict:
        """Run all configured providers, deduplicate and upsert active advisories into PostgreSQL."""
        total_fetched = 0
        total_inserted = 0
        total_updated = 0
        now_utc = datetime.now(timezone.utc)

        # 1. Fetch from all providers with error containment
        results: List[List[NormalizedAdvisory]] = await asyncio.gather(
            *[p.get_advisories() for p in self.providers],
            return_exceptions=False,
        )

        all_advisories: List[NormalizedAdvisory] = []
        for provider_alerts in results:
            all_advisories.extend(provider_alerts)
        total_fetched = len(all_advisories)

        # 2. Deduplicate and upsert into database
        for item in all_advisories:
            existing = (
                db.query(Advisory)
                .filter(
                    Advisory.authority == item.authority,
                    Advisory.source_id == item.source_id,
                )
                .first()
            )

            is_active = item.effective_at <= now_utc <= item.expires_at

            if existing:
                existing.severity = item.severity
                existing.headline = item.headline
                existing.description = item.description
                existing.action_guidance = item.action_guidance
                existing.expires_at = item.expires_at
                existing.is_active = is_active
                existing.updated_at = now_utc
                total_updated += 1
            else:
                new_advisory = Advisory(
                    source_id=item.source_id,
                    authority=item.authority,
                    source_url=item.source_url,
                    hazard_type=item.hazard_type,
                    severity=item.severity,
                    official_level=item.official_level,
                    urgency=item.urgency,
                    certainty=item.certainty,
                    issued_at=item.issued_at,
                    effective_at=item.effective_at,
                    expires_at=item.expires_at,
                    is_active=is_active,
                    granularity=item.granularity,
                    state=item.state,
                    district=item.district,
                    subdivision=item.subdivision,
                    latitude=item.latitude,
                    longitude=item.longitude,
                    radius_km=item.radius_km,
                    polygon_geojson=item.polygon_geojson,
                    headline=item.headline,
                    description=item.description,
                    action_guidance=item.action_guidance,
                    raw_payload=item.raw_payload,
                )
                db.add(new_advisory)
                total_inserted += 1

        # 3. Mark naturally expired advisories as inactive
        expired_count = self.prune_expired(db, now_utc)

        db.commit()

        logger.info(
            f"[AdvisoryIngestion] Ingestion cycle complete: {total_fetched} fetched, "
            f"{total_inserted} inserted, {total_updated} updated, {expired_count} expired."
        )

        return {
            "fetched": total_fetched,
            "inserted": total_inserted,
            "updated": total_updated,
            "expired": expired_count,
            "timestamp": now_utc.isoformat(),
        }

    def prune_expired(self, db: Session, now_utc: Optional[datetime] = None) -> int:
        """Mark alerts whose expires_at timestamp is in the past as is_active = False."""
        now = now_utc or datetime.now(timezone.utc)
        expired = (
            db.query(Advisory)
            .filter(
                Advisory.is_active.is_(True),
                Advisory.expires_at < now,
            )
            .all()
        )
        for item in expired:
            item.is_active = False
            item.updated_at = now
        db.commit()
        return len(expired)


advisory_ingestion_service = AdvisoryIngestionService()
