from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AnalystQueueRead(BaseModel):
    id: UUID
    application_id: UUID
    analyst_id: UUID | None

    priority: int
    priority_reason: str | None

    status: str

    assigned_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None

    sla_deadline: datetime
    sla_breached: bool

    routing_reason: str | None
    score_at_routing: int | None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
