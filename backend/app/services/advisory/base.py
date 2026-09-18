"""Abstract base class for all environmental advisory source providers."""

from abc import ABC, abstractmethod
import logging
from typing import Any, List

from app.services.advisory.models import NormalizedAdvisory

logger = logging.getLogger(__name__)


class BaseAdvisoryProvider(ABC):
    """Contract for official hazard data provider adapters."""

    @property
    @abstractmethod
    def authority(self) -> str:
        """Name of the issuing authority (e.g. IMD, NDMA, CWC, INCOIS, CPCB)."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Distinct human-readable provider name."""
        pass

    @abstractmethod
    async def fetch_raw(self) -> Any:
        """Fetch raw payload from official government endpoint or feed."""
        pass

    @abstractmethod
    def parse_payload(self, raw_data: Any) -> List[NormalizedAdvisory]:
        """Parse source payload into normalized internal advisory models."""
        pass

    async def get_advisories(self) -> List[NormalizedAdvisory]:
        """Fetch and parse advisories with graceful error containment.

        Ensures that a single provider failure never crashes the application or weather pipeline.
        """
        try:
            raw_data = await self.fetch_raw()
            if not raw_data:
                return []
            advisories = self.parse_payload(raw_data)
            logger.info(f"[{self.authority}] Ingested {len(advisories)} normalized advisories via {self.name}")
            return advisories
        except Exception as exc:
            logger.warning(f"[{self.authority}] Provider fetch failed on {self.name}: {exc}", exc_info=True)
            return []
