from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class SimilarCaseRead(BaseModel):
    id: UUID
    application_id: UUID

    matched_application_id: UUID
    match_score: float

    features_snapshot: dict[str, Any]
    outcome_snapshot: dict[str, Any]

    method: str
    created_at: datetime

    class Config:
        from_attributes = True
