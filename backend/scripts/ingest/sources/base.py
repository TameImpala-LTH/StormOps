"""Base protocol and data structures for gazetteer source adapters."""

from abc import ABC, abstractmethod
from typing import Any, List, Tuple
from ..schema import EntityAlias, EntityGeometry, GeographicEntity


class SourceAdapter(ABC):
    """Abstract interface that every geographic source adapter must implement."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the unique name of this data source (e.g. 'LGD', 'CENSUS_2011', 'OSM', 'CURATED_URBAN')."""
        pass

    @abstractmethod
    def parse(
        self, data_or_path: Any
    ) -> Tuple[List[GeographicEntity], List[EntityAlias], List[EntityGeometry]]:
        """Parse raw or structured source input and produce normalized entities, aliases, and geometries.

        Returns:
            (entities, aliases, geometries)
        """
        pass
