"""Deterministic deduplication and homonym preservation engine for Indian geographic entities.

Merge Criteria
--------------
Two entities are considered TRUE duplicates if and only if ALL of the following
applicable conditions are simultaneously satisfied:

    1.  Identical normalized_name.
    2.  Same entity_type (e.g. VILLAGE and STATUTORY_TOWN are never merged).
    3.  Same country_code (always "IN" for this pipeline).
    4.  If both state_id values are non-None: they must be equal.
        → Different states: never merged, even if the name is the same.
    5.  If both district_id values are non-None: they must be equal.
        → Same state, different districts: NOT merged; these are legitimate homonyms
          (e.g. "Rampur" appears in dozens of districts across India).
    6.  If both subdistrict_id values are non-None: they must be equal.
    7.  Definitive identity: same source AND same non-empty source_id.
        (A later-version record from the same source supersedes the earlier one.)
    8.  Spatial proximity fallback: only when conditions 1–6 are met AND
        coordinates for both are present AND the haversine distance ≤ max_distance_km.

Homonym Preservation
--------------------
Any pair of entities that share a normalized name but fail ANY of the above
conditions (e.g. same state/district but different subdistrict, different
geographic coordinates > 5 km apart, or different entity types) are treated as
DISTINCT legitimate homonyms and are both preserved in the output.
"""

import math
from typing import Dict, List, Tuple

from .schema import GeographicEntity


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    r = 6371.0  # Earth's mean radius
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

def are_true_duplicates(
    e1: GeographicEntity,
    e2: GeographicEntity,
    max_distance_km: float = 5.0,
) -> bool:
    """Return True iff e1 and e2 represent the exact same geographic unit.

    See module-level docstring for the full, documented merge criteria.
    All applicable criteria must be satisfied; no single criterion alone is
    sufficient (except the definitive source+source_id match, which still
    requires name, type, and hierarchy consistency).
    """
    # Criterion 1: identical normalized name (required; no exceptions)
    if e1.normalized_name != e2.normalized_name:
        return False

    # Criterion 2: same entity type (VILLAGE != STATUTORY_TOWN, etc.)
    if e1.entity_type != e2.entity_type:
        return False

    # Criterion 3: same country (always "IN" in this pipeline)
    if e1.country_code != e2.country_code:
        return False

    # Criterion 4: cross-state merging is never permitted
    if e1.state_id and e2.state_id and e1.state_id != e2.state_id:
        return False

    # Criterion 5: cross-district merging is never permitted
    # (e.g. "Rampur" in Bareilly district ≠ "Rampur" in Moradabad district)
    if e1.district_id and e2.district_id and e1.district_id != e2.district_id:
        return False

    # Criterion 6: cross-subdistrict merging is never permitted when both are
    # known and differ
    if e1.subdistrict_id and e2.subdistrict_id and e1.subdistrict_id != e2.subdistrict_id:
        return False

    # Criterion 7: definitive identity — same source AND same non-empty source_id
    if (
        e1.source == e2.source
        and e1.source_id
        and e2.source_id
        and e1.source_id == e2.source_id
    ):
        return True

    # Criterion 8: spatial proximity fallback (only when hierarchy constraints
    # above are all satisfied *and* coordinates are available for both)
    both_have_coords = (
        e1.latitude is not None
        and e1.longitude is not None
        and e2.latitude is not None
        and e2.longitude is not None
    )
    if both_have_coords:
        dist = haversine_distance_km(e1.latitude, e1.longitude, e2.latitude, e2.longitude)
        # Within 5 km and all hierarchy criteria satisfied → true duplicate
        return dist <= max_distance_km

    # Cannot confirm identity without source_id match or spatial proximity
    return False


# ---------------------------------------------------------------------------
# Deduplication engine
# ---------------------------------------------------------------------------

def deduplicate_entities(
    entities: List[GeographicEntity],
) -> Tuple[List[GeographicEntity], List[str]]:
    """Deduplicate an entity list while strictly preserving legitimate homonyms.

    Entities are sorted by (source, source_id) before processing to guarantee
    deterministic output regardless of input ordering.

    Returns:
        (deduplicated_entities, audit_log)
        - deduplicated_entities: list with true duplicates merged
        - audit_log: human-readable record of every merge and every preserved homonym
    """
    # Deterministic sort: process entities in a fixed, stable order
    sorted_entities = sorted(
        entities,
        key=lambda e: (e.source or "", e.source_id or "", e.id),
    )

    deduped: List[GeographicEntity] = []
    audit_log: List[str] = []

    # Group by normalized_name for O(K²) within same-name buckets
    name_buckets: Dict[str, List[GeographicEntity]] = {}
    for e in sorted_entities:
        name_buckets.setdefault(e.normalized_name, []).append(e)

    for norm_name, candidates in sorted(name_buckets.items()):
        if len(candidates) == 1:
            deduped.append(candidates[0])
            continue

        merged_in_bucket: List[GeographicEntity] = []

        for cand in candidates:
            merged = False
            for existing in merged_in_bucket:
                if are_true_duplicates(existing, cand):
                    # Merge: prefer higher confidence, fill missing coordinates
                    if cand.confidence > existing.confidence:
                        existing.confidence = cand.confidence
                    if existing.latitude is None and cand.latitude is not None:
                        existing.latitude = cand.latitude
                        existing.longitude = cand.longitude
                    if not existing.source_id and cand.source_id:
                        existing.source_id = cand.source_id
                    audit_log.append(
                        f"MERGE: '{cand.name}' "
                        f"(source={cand.source}, source_id={cand.source_id}, "
                        f"type={cand.entity_type}, "
                        f"state={cand.state_id}, district={cand.district_id}) "
                        f"→ '{existing.name}' (id={existing.id})"
                    )
                    merged = True
                    break

            if not merged:
                merged_in_bucket.append(cand)
                if len(merged_in_bucket) > 1:
                    audit_log.append(
                        f"HOMONYM PRESERVED: '{cand.name}' "
                        f"(type={cand.entity_type}, "
                        f"state={cand.state_id}, district={cand.district_id}, "
                        f"subdistrict={cand.subdistrict_id}) "
                        f"kept as distinct from {len(merged_in_bucket) - 1} existing entity/ies "
                        f"with the same normalized name"
                    )

        deduped.extend(merged_in_bucket)

    return deduped, audit_log
