from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class DecisionRead(BaseModel):
    id: UUID
    application_id: UUID

    scoring_result_id: UUID | None
    analyst_id: UUID | None

    decision_type: str
    decision_outcome: str

    approved_terms: dict[str, Any] | None
    conditions: list[Any] | None

    reasoning: str | None
    reasoning_category: str | None

    override_flag: bool
    override_direction: str | None
    override_justification: str | None
    override_approved_by: UUID | None
    override_approved_at: datetime | None

    review_time_seconds: int | None

    created_at: datetime

    class Config:
        from_attributes = True
