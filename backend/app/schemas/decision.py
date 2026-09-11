"""Pydantic schemas for WeatherGPT Decision Engine."""

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class DecisionFactor(BaseModel):
    """Specific meteorological factor influencing a decision recommendation."""

    metric: str = Field(..., description="Meteorological metric name (e.g. precipitation_probability, temperature)")
    value: Any = Field(..., description="Metric value (e.g. 75, 'Moderate rain', 28.5)")
    impact: str = Field("neutral", description="Impact on decision: positive | negative | neutral")


class DecisionResponse(BaseModel):
    """Normalized decision engine output model."""

    type: str = Field(..., description="Decision type: umbrella | outdoor_activity | travel | clothing")
    recommendation: str = Field(..., description="Recommendation result: recommended | not_recommended | caution | neutral | unknown")
    confidence: str = Field("high", description="Confidence level: high | medium | low")
    summary: str = Field(..., description="Human-readable decision recommendation summary")
    factors: List[DecisionFactor] = Field(default_factory=list, description="Key meteorological factors driving decision")

