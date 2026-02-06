from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AnalystQueueRead(BaseModel):
    id: UUID
    application_id: UUID
    analyst_id: UUID | None = None

    priority: int
    priority_reason: str | None = None

    status: str

    assigned_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    sla_deadline: datetime
    sla_breached: bool

    routing_reason: str | None = None
    score_at_routing: int | None = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnalystQueueListResponse(BaseModel):
    items: list[AnalystQueueRead]


class AnalystQueueSummaryResponse(BaseModel):
    total_pending: int
    total_assigned: int
    total_in_progress: int
    approaching_sla: int
    breached_sla: int
    by_priority: dict[str, int]
