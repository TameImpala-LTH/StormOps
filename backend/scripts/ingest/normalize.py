"""Deterministic text normalization for gazetteer entity matching.

Normalization converts variations in casing, punctuation, diacritics, and whitespace
into a canonical search key while strictly preserving canonical display names and
geographic qualifiers.
"""

import re
import unicodedata
from typing import List, Tuple


def normalize_name(text: str) -> str:
    """Normalize a place or locality name for deterministic indexing and matching.

    - Decomposes and strips Unicode combining diacritics (NFKD)
    - Converts to lowercase
    - Converts hyphens and forward slashes to spaces
    - Removes non-alphanumeric punctuation while retaining Indic script ranges
    - Collapses multiple whitespace characters into a single space
    """
    if not text:
        return ""

    # Unicode NFKD normalization to separate base characters from diacritics
    nfkd = unicodedata.normalize("NFKD", text)
    # Filter out combining diacritical marks
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))

    # Lowercase
    lowered = stripped.lower()

    # Replace hyphens, underscores, slashes with spaces (e.g. "Park-Street" -> "park street")
    replaced = re.sub(r"[\-_\/\\]+", " ", lowered)

    # Remove extraneous punctuation (periods, commas, apostrophes, quotes, parens)
    # Retain standard English alphanumeric and Indic Unicode blocks (\u0900-\u0D7F)
    cleaned = re.sub(r"[^\w\s\u0900-\u0D7F]", "", replaced)

    # Collapse whitespace
    return re.sub(r"\s+", " ", cleaned).strip()


def split_geographic_qualifiers(text: str) -> Tuple[str, List[str]]:
    """Split a location phrase containing comma-separated geographic qualifiers.

    Example:
        'Park Street, Kolkata, West Bengal' -> ('Park Street', ['Kolkata', 'West Bengal'])
    """
    if not text or "," not in text:
        return text.strip(), []

    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        return "", []

    primary = parts[0]
    qualifiers = parts[1:]
    return primary, qualifiers


def is_equivalent_normalized(name_a: str, name_b: str) -> bool:
    """Check whether two strings evaluate to the exact same normalized search key."""
    return normalize_name(name_a) == normalize_name(name_b)
