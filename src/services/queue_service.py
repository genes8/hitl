from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.analyst_queue import AnalystQueue
from src.models.application import Application


@dataclass(frozen=True)
class QueueDefaults:
    """Default queue behavior.

    These are intentionally constants at the service layer for now; in later
    phases they can be made tenant-configurable.
    """

    sla_hours: int = 8


class QueueService:
    """Encapsulates queue-related business rules (Phase 2.2)."""

    def __init__(self, *, defaults: QueueDefaults | None = None) -> None:
        self._defaults = defaults or QueueDefaults()

    async def create_queue_entry(
        self,
        session: AsyncSession,
        *,
        application_id: UUID,
        score_at_routing: int | None,
        routing_reason: str | None,
        is_vip: bool = False,
    ) -> AnalystQueue:
        """Create an analyst queue entry for an application.

        Spec (hitl/todo.md TODO-2.2.1):
        - priority via calculate_queue_priority()
        - SLA deadline defaults to 8h from creation
        - store score_at_routing + routing_reason
        """

        app = await session.get(Application, application_id)
        if app is None:
            raise ValueError("Application not found")

        loan_amount = float((app.loan_request or {}).get("loan_amount") or 0)
        now = datetime.now(tz=timezone.utc)
        sla_deadline = now + timedelta(hours=self._defaults.sla_hours)
        sla_hours_remaining = float(self._defaults.sla_hours)

        # Priority is computed by a database function so it stays consistent with
        # SQL-side ordering and future DB-level logic.
        q = text(
            "SELECT calculate_queue_priority(:score, :loan_amount, :is_vip, :sla_hours_remaining)"
        )
        r = await session.execute(
            q,
            {
                "score": int(score_at_routing or 0),
                "loan_amount": loan_amount,
                "is_vip": bool(is_vip),
                "sla_hours_remaining": sla_hours_remaining,
            },
        )
        priority = int(r.scalar_one())

        entry = AnalystQueue(
            application_id=application_id,
            analyst_id=None,
            priority=priority,
            priority_reason=None,
            status="pending",
            assigned_at=None,
            started_at=None,
            completed_at=None,
            sla_deadline=sla_deadline,
            sla_breached=False,
            routing_reason=routing_reason,
            score_at_routing=score_at_routing,
        )

        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        return entry
