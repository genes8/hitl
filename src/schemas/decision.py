from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DecisionRead(BaseModel):
    id: UUID
    application_id: UUID

    decision_type: str
    decision_outcome: str

    reasoning: str | None = None
    reasoning_category: str | None = None

    override_flag: bool

    created_at: datetime

    class Config:
        from_attributes = True
