from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class QueueInfoRead(BaseModel):
    """Minimal queue entry info embedded in ApplicationRead.

    This is intentionally a subset of AnalystQueue fields; it is meant for the
    application detail endpoint (TODO-2.1.3).
    """

    id: UUID
    application_id: UUID

    status: str
    priority: int

    analyst_id: UUID | None = None

    sla_deadline: datetime
    sla_breached: bool

    assigned_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    routing_reason: str | None = None
    score_at_routing: int | None = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
