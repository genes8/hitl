from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.analyst_queue import AnalystQueue
from src.models.application import Application


async def list_queue_entries(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    status: str | None = None,
    analyst_id: UUID | None = None,
    priority_max: int | None = None,
    sort_by: str = "priority",
    sort_order: str = "asc",
    limit: int = 50,
    offset: int = 0,
) -> list[AnalystQueue]:
    """List queue entries for a tenant.

    NOTE: analyst_queues has no tenant_id; we enforce isolation via applications.tenant_id.
    """

    # Defense-in-depth normalization (endpoint also validates).
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    q = (
        select(AnalystQueue)
        .join(Application, Application.id == AnalystQueue.application_id)
        .where(Application.tenant_id == tenant_id)
    )

    if status is not None:
        q = q.where(AnalystQueue.status == status)
    if analyst_id is not None:
        q = q.where(AnalystQueue.analyst_id == analyst_id)
    if priority_max is not None:
        q = q.where(AnalystQueue.priority <= priority_max)

    sort_col = {
        "priority": AnalystQueue.priority,
        "created_at": AnalystQueue.created_at,
        "sla_deadline": AnalystQueue.sla_deadline,
    }.get(sort_by, AnalystQueue.priority)

    if sort_order == "desc":
        q = q.order_by(sort_col.desc(), AnalystQueue.id.desc())
    else:
        q = q.order_by(sort_col.asc(), AnalystQueue.id.asc())

    q = q.offset(offset).limit(limit)
    r = await session.execute(q)
    return list(r.scalars().all())


async def queue_summary(
    session: AsyncSession,
    *,
    tenant_id: UUID,
) -> dict:
    """Return a summary payload per hitl/todo.md TODO-2.2.1."""

    now = datetime.now(timezone.utc)
    approaching_cutoff = now + timedelta(hours=2)

    base = (
        select(AnalystQueue)
        .join(Application, Application.id == AnalystQueue.application_id)
        .where(Application.tenant_id == tenant_id)
        .where(AnalystQueue.status.in_(["pending", "assigned", "in_progress"]))
    ).subquery()

    totals_q = select(
        # totals by status
        func.sum(sa.case((base.c.status == "pending", 1), else_=0)).label("total_pending"),
        func.sum(sa.case((base.c.status == "assigned", 1), else_=0)).label("total_assigned"),
        func.sum(sa.case((base.c.status == "in_progress", 1), else_=0)).label("total_in_progress"),
        # SLA metrics
        func.sum(
            sa.case(
                (sa.and_(base.c.sla_deadline > now, base.c.sla_deadline <= approaching_cutoff), 1),
                else_=0,
            )
        ).label("approaching_sla"),
        func.sum(sa.case((base.c.sla_deadline <= now, 1), else_=0)).label("breached_sla"),
        # priority buckets (lower number == higher priority)
        func.sum(sa.case((base.c.priority <= 20, 1), else_=0)).label("priority_high"),
        func.sum(sa.case((sa.and_(base.c.priority > 20, base.c.priority <= 50), 1), else_=0)).label("priority_medium"),
        func.sum(sa.case((base.c.priority > 50, 1), else_=0)).label("priority_low"),
    )

    totals = (await session.execute(totals_q)).mappings().one()

    return {
        "total_pending": int(totals["total_pending"] or 0),
        "total_assigned": int(totals["total_assigned"] or 0),
        "total_in_progress": int(totals["total_in_progress"] or 0),
        "approaching_sla": int(totals["approaching_sla"] or 0),
        "breached_sla": int(totals["breached_sla"] or 0),
        "by_priority": {
            "high": int(totals["priority_high"] or 0),
            "medium": int(totals["priority_medium"] or 0),
            "low": int(totals["priority_low"] or 0),
        },
    }
