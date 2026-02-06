from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ScoringResultRead(BaseModel):
    id: UUID
    application_id: UUID

    model_id: str
    model_version: str

    score: int
    probability_default: float
    risk_category: str
    routing_decision: str

    threshold_config_id: UUID | None

    features: dict[str, Any]
    shap_values: dict[str, Any]
    top_factors: dict[str, Any]

    scoring_time_ms: int
    created_at: datetime

    class Config:
        from_attributes = True
