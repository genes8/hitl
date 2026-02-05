from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class DecisionRead(BaseModel):
    id: UUID
    application_id: UUID

    scoring_result_id: UUID | None = None
    analyst_id: UUID | None = None

    decision_type: str
    decision_outcome: str

    approved_terms: dict[str, Any] | None = None
    conditions: list[Any] | None = None

    reasoning: str | None = None
    reasoning_category: str | None = None

    override_flag: bool
    override_direction: str | None = None
    override_justification: str | None = None
    override_approved_by: UUID | None = None
    override_approved_at: datetime | None = None

    review_time_seconds: int | None = None

    created_at: datetime

    class Config:
        from_attributes = True
