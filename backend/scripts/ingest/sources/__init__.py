"""Source adapters package for the India Gazetteer ingestion pipeline.

Each adapter reads a single geographic data source and returns a normalized
tuple of (entities, aliases, geometries) conforming to the SourceAdapter contract
defined in base.py.

Adapter execution order (fixed and deterministic):
    1. LGDAdapter      – current administrative / local-government hierarchy
    2. CensusAdapter   – Census 2011 historical settlement baseline
    3. OSMAdapter      – OSM locality / neighbourhood enrichment
    4. CuratedAdapter  – existing curated urban locality index
"""

from .base import SourceAdapter
from .lgd import LGDAdapter
from .census import CensusAdapter
from .osm import OSMAdapter
from .curated import CuratedAdapter

__all__ = [
    "SourceAdapter",
    "LGDAdapter",
    "CensusAdapter",
    "OSMAdapter",
    "CuratedAdapter",
]
