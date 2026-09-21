"""Authoritative alias registry and deterministic alias generator for Indian geographic entities."""

from typing import Dict, List, Tuple
from .normalize import normalize_name
from .schema import AliasType, EntityAlias, GeographicEntity

# Authoritative historical, renamed, and standard administrative aliases
# Mapping: Canonical Entity Name -> List of (Alias, AliasType, Language, Confidence, Source)
AUTHORITATIVE_HISTORICAL_ALIASES: Dict[str, List[Tuple[str, AliasType, str, float, str]]] = {
    "Kolkata": [
        ("Calcutta", AliasType.HISTORICAL, "en", 1.0, "OFFICIAL_GAZETTE"),
        ("কলকাতা", AliasType.LOCAL_SCRIPT, "bn", 1.0, "VERNACULAR_SCRIPT"),
    ],
    "Mumbai": [
        ("Bombay", AliasType.HISTORICAL, "en", 1.0, "OFFICIAL_GAZETTE"),
        ("मुंबई", AliasType.LOCAL_SCRIPT, "mr", 1.0, "VERNACULAR_SCRIPT"),
    ],
    "Chennai": [
        ("Madras", AliasType.HISTORICAL, "en", 1.0, "OFFICIAL_GAZETTE"),
        ("சென்னை", AliasType.LOCAL_SCRIPT, "ta", 1.0, "VERNACULAR_SCRIPT"),
    ],
    "Bengaluru": [
        ("Bangalore", AliasType.HISTORICAL, "en", 1.0, "OFFICIAL_GAZETTE"),
        ("பெங்களூரு", AliasType.LOCAL_SCRIPT, "ta", 1.0, "VERNACULAR_SCRIPT"),
    ],
    "Pune": [
        ("Poona", AliasType.HISTORICAL, "en", 1.0, "OFFICIAL_GAZETTE"),
    ],
    "Gurugram": [
        ("Gurgaon", AliasType.HISTORICAL, "en", 1.0, "OFFICIAL_GAZETTE"),
    ],
    "Visakhapatnam": [
        ("Vizag", AliasType.COLLOQUIAL, "en", 1.0, "OFFICIAL_GAZETTE"),
        ("Waltair", AliasType.HISTORICAL, "en", 0.95, "OFFICIAL_GAZETTE"),
    ],
    "Prayagraj": [
        ("Allahabad", AliasType.HISTORICAL, "en", 1.0, "OFFICIAL_GAZETTE"),
    ],
    "Chhatrapati Sambhajinagar": [
        ("Aurangabad", AliasType.HISTORICAL, "en", 1.0, "OFFICIAL_GAZETTE"),
    ],
    "Dharashiv": [
        ("Osmanabad", AliasType.HISTORICAL, "en", 1.0, "OFFICIAL_GAZETTE"),
    ],
    "Varanasi": [
        ("Benares", AliasType.HISTORICAL, "en", 1.0, "OFFICIAL_GAZETTE"),
        ("Banaras", AliasType.COLLOQUIAL, "en", 1.0, "OFFICIAL_GAZETTE"),
        ("Kashi", AliasType.HISTORICAL, "en", 1.0, "OFFICIAL_GAZETTE"),
    ],
    "Vadodara": [
        ("Baroda", AliasType.HISTORICAL, "en", 1.0, "OFFICIAL_GAZETTE"),
    ],
    "Thiruvananthapuram": [
        ("Trivandrum", AliasType.HISTORICAL, "en", 1.0, "OFFICIAL_GAZETTE"),
    ],
    "Shimla": [
        ("Simla", AliasType.HISTORICAL, "en", 1.0, "OFFICIAL_GAZETTE"),
    ],
    "Kochi": [
        ("Cochin", AliasType.HISTORICAL, "en", 1.0, "OFFICIAL_GAZETTE"),
    ],
    "Udhagamandalam": [
        ("Ooty", AliasType.COLLOQUIAL, "en", 1.0, "OFFICIAL_GAZETTE"),
    ],
}


def generate_deterministic_aliases(entity: GeographicEntity) -> List[EntityAlias]:
    """Generate deterministic, non-speculative aliases for a geographic entity with complete provenance."""
    aliases: List[EntityAlias] = []
    seen_normalized = {entity.normalized_name}

    # 1. Authoritative official renamings / historical names
    canonical_name = entity.name.strip()
    if canonical_name in AUTHORITATIVE_HISTORICAL_ALIASES:
        for alias_str, a_type, lang, conf, src in AUTHORITATIVE_HISTORICAL_ALIASES[canonical_name]:
            norm_alias = normalize_name(alias_str)
            if norm_alias not in seen_normalized:
                seen_normalized.add(norm_alias)
                aliases.append(
                    EntityAlias(
                        entity_id=entity.id,
                        alias=alias_str,
                        normalized_alias=norm_alias,
                        alias_type=a_type,
                        language=lang,
                        confidence=conf,
                        source=src,
                    )
                )

    # 2. Road junction variants (Bengali / Hindi "More" -> "Crossing", "Mor")
    if canonical_name.lower().endswith(" more"):
        base_name = canonical_name[:-5].strip()
        junction_variants = [
            (f"{base_name} Crossing", AliasType.COLLOQUIAL),
            (f"{base_name} Mor", AliasType.PHONETIC),
        ]
        for v_name, v_type in junction_variants:
            v_norm = normalize_name(v_name)
            if v_norm not in seen_normalized:
                seen_normalized.add(v_norm)
                aliases.append(
                    EntityAlias(
                        entity_id=entity.id,
                        alias=v_name,
                        normalized_alias=v_norm,
                        alias_type=v_type,
                        language="en",
                        confidence=0.95,
                        source="DETERMINISTIC_JUNCTION_RULE",
                    )
                )

    # 3. Compounding & De-compounding rules (e.g. "New Town" <-> "Newtown", "Salt Lake" <-> "Saltlake")
    parts = canonical_name.split()
    if len(parts) == 2 and len(canonical_name) <= 20:
        compounded = "".join(parts)
        c_norm = normalize_name(compounded)
        if c_norm not in seen_normalized:
            seen_normalized.add(c_norm)
            aliases.append(
                EntityAlias(
                    entity_id=entity.id,
                    alias=compounded,
                    normalized_alias=c_norm,
                    alias_type=AliasType.COLLOQUIAL,
                    language="en",
                    confidence=0.90,
                    source="DETERMINISTIC_COMPOUND_RULE",
                )
            )

    return aliases
