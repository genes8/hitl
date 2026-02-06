from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


QueueStatus = Literal["pending", "assigned", "in_progress", "completed"]


class AnalystQueueRead(BaseModel):
    id: UUID
    application_id: UUID
    analyst_id: UUID | None

    priority: int
    priority_reason: str | None

    status: QueueStatus

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


class AnalystQueueListResponse(BaseModel):
    items: list[AnalystQueueRead] = Field(default_factory=list)


class AnalystQueueSummaryResponse(BaseModel):
    total_pending: int
    total_assigned: int
    total_in_progress: int

    approaching_sla: int
    breached_sla: int

    by_priority: dict[str, int]
