"""India Locality Intelligence & Dataset Management Service.

Provides a structured, high-confidence, scalable dataset and index of Indian urban localities,
suburbs, and neighbourhoods with full administrative hierarchy (locality, city, district,
subdivision, state, country, coordinates).
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import app.core.compat  # noqa: F401
from app.schemas.query import GeocodedLocationSchema

logger = logging.getLogger(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "india_localities.json")


def _normalize_name(text: str) -> str:
    """Normalize query text for lookup."""
    lowered = text.strip().lower()
    # Collapse multiple spaces and remove common trailing words
    cleaned = re.sub(r"[^\w\s]", "", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()


class IndiaLocalityRecord:
    """Structured representation of an Indian urban locality."""

    __slots__ = (
        "locality",
        "parent_city",
        "parent_state",
        "district",
        "subdivision",
        "latitude",
        "longitude",
        "timezone",
        "country",
        "country_code",
        "aliases",
        "confidence",
        "source",
    )

    def __init__(
        self,
        locality: str,
        parent_city: str,
        parent_state: str,
        district: Optional[str] = None,
        subdivision: Optional[str] = None,
        latitude: float = 0.0,
        longitude: float = 0.0,
        timezone: str = "Asia/Kolkata",
        country: str = "India",
        country_code: str = "IN",
        aliases: Optional[List[str]] = None,
        confidence: float = 0.95,
        source: str = "canonical_urban_index",
    ):
        self.locality = locality
        self.parent_city = parent_city
        self.parent_state = parent_state
        self.district = district or parent_city
        self.subdivision = subdivision or parent_city
        self.latitude = latitude
        self.longitude = longitude
        self.timezone = timezone
        self.country = country
        self.country_code = country_code
        self.aliases = aliases or []
        self.confidence = confidence
        self.source = source

    def to_geocoded_schema(self) -> GeocodedLocationSchema:
        """Convert record to canonical GeocodedLocationSchema."""
        components = []
        for part in [self.locality, self.parent_city, self.parent_state, self.country or "India"]:
            if part and (not components or part.lower() != components[-1].lower()):
                components.append(part)
        display_name = ", ".join(components)
        return GeocodedLocationSchema(
            name=display_name,
            country=self.country,
            country_code=self.country_code,
            admin1=self.parent_state,
            state=self.parent_state,
            district=self.district,
            subdivision=self.subdivision,
            city=self.parent_city,
            locality=self.locality,
            latitude=self.latitude,
            longitude=self.longitude,
            timezone=self.timezone,
        )


class IndiaLocalityService:
    """Service managing high-confidence Indian locality index and administrative validation."""

    def __init__(self, data_path: str = DATA_PATH):
        self._data_path = data_path
        self._records: List[IndiaLocalityRecord] = []
        self._index: Dict[str, List[IndiaLocalityRecord]] = {}
        self._states: Set[str] = set()
        self._cities: Set[str] = set()
        self._load_dataset()

    def _load_dataset(self) -> None:
        """Load and index the structured India localities dataset."""
        if not os.path.exists(self._data_path):
            logger.warning(f"India localities dataset not found at {self._data_path}")
            return

        try:
            with open(self._data_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for item in data:
                rec = IndiaLocalityRecord(
                    locality=item["locality"],
                    parent_city=item["parent_city"],
                    parent_state=item["parent_state"],
                    district=item.get("district"),
                    subdivision=item.get("subdivision"),
                    latitude=float(item["latitude"]),
                    longitude=float(item["longitude"]),
                    timezone=item.get("timezone", "Asia/Kolkata"),
                    country=item.get("country", "India"),
                    country_code=item.get("country_code", "IN"),
                    aliases=item.get("aliases", []),
                    confidence=float(item.get("confidence", 0.95)),
                    source=item.get("source", "canonical_urban_index"),
                )
                self._records.append(rec)
                self._states.add(rec.parent_state)
                self._cities.add(rec.parent_city)

                # Primary key indexing
                norm_name = _normalize_name(rec.locality)
                self._index.setdefault(norm_name, []).append(rec)

                # Aliases indexing
                for alias in rec.aliases:
                    norm_alias = _normalize_name(alias)
                    self._index.setdefault(norm_alias, []).append(rec)

            logger.info(
                f"Loaded India Locality Dataset: {len(self._records)} localities across "
                f"{len(self._cities)} cities and {len(self._states)} states."
            )
        except Exception as exc:
            logger.error(f"Failed to load India locality dataset: {exc}")

    def find_locality(
        self,
        name: str,
        context_city: Optional[str] = None,
        context_state: Optional[str] = None,
    ) -> Optional[GeocodedLocationSchema]:
        """Find an Indian locality by name or alias, applying city/state disambiguation when multiple candidates exist."""
        norm = _normalize_name(name)
        candidates = self._index.get(norm)
        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0].to_geocoded_schema()

        # Disambiguation with active context
        if context_city:
            ctx_c = context_city.strip().lower()
            for cand in candidates:
                if cand.parent_city.lower() == ctx_c:
                    return cand.to_geocoded_schema()

        if context_state:
            ctx_s = context_state.strip().lower()
            for cand in candidates:
                if cand.parent_state.lower() == ctx_s:
                    return cand.to_geocoded_schema()

        # Default to the candidate with highest confidence / first canonical entry
        best = max(candidates, key=lambda c: c.confidence)
        return best.to_geocoded_schema()

    def get_known_locality_record(self, name: str) -> Optional[IndiaLocalityRecord]:
        """Retrieve the raw IndiaLocalityRecord for administrative comparison."""
        norm = _normalize_name(name)
        candidates = self._index.get(norm)
        return candidates[0] if candidates else None

    def validate_administrative_hierarchy(
        self,
        provider_result: GeocodedLocationSchema,
        query_locality_name: str,
    ) -> bool:
        """Validate whether a provider-resolved location matches the authoritative administrative hierarchy for this Indian locality.

        Rejects foreign results (e.g., Bangladesh village) or mismatched states (e.g. Basavanagudi in Andhra Pradesh).
        """
        known_rec = self.get_known_locality_record(query_locality_name)
        if not known_rec:
            # If not a known Indian locality, allow global provider result unless it claims India with invalid country code
            if (provider_result.country or "").strip().lower() == "india" and provider_result.country_code != "IN":
                return False
            return True

        # Strict country verification
        if provider_result.country_code != "IN" and "india" not in (provider_result.country or "").lower():
            logger.warning(
                "Administrative validation failed for '%s': provider returned country '%s', expected 'India'",
                query_locality_name, provider_result.country,
            )
            return False

        # State verification
        res_state = (provider_result.state or provider_result.admin1 or "").strip().lower()
        exp_state = known_rec.parent_state.strip().lower()
        if res_state and res_state != exp_state:
            logger.warning(
                "Administrative validation failed for '%s': provider returned state '%s', expected '%s'",
                query_locality_name, res_state, exp_state,
            )
            return False

        return True

    def get_dataset_stats(self) -> Dict[str, Any]:
        """Return dataset coverage statistics."""
        return {
            "total_localities": len(self._records),
            "total_cities": len(self._cities),
            "total_states": len(self._states),
            "cities": sorted(self._cities),
            "states": sorted(self._states),
        }


# Singleton instance
india_locality_service = IndiaLocalityService()
