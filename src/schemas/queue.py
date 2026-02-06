from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class QueueInfoRead(BaseModel):
    id: UUID
    application_id: UUID

    status: str
    priority: int

    analyst_id: UUID | None = None

    assigned_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    sla_deadline: datetime
    sla_breached: bool

    routing_reason: str | None = None
    score_at_routing: int | None = None

    class Config:
        from_attributes = True
