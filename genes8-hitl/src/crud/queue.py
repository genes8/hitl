from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.analyst_queue import AnalystQueue
from src.models.application import Application


def _priority_bucket(priority: int) -> str:
    # Lower number == higher priority.
    if priority <= 20:
        return "high"
    if priority <= 50:
        return "medium"
    return "low"


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

    if limit < 1:
        limit = 1
    if limit > 200:
        limit = 200
    if offset < 0:
        offset = 0

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
    """Return a summary payload similar to hitl/todo.md TODO-2.2.1."""

    now = datetime.now(timezone.utc)
    approaching_cutoff = now + timedelta(hours=2)

    base = (
        select(AnalystQueue)
        .join(Application, Application.id == AnalystQueue.application_id)
        .where(Application.tenant_id == tenant_id)
        .where(AnalystQueue.status.in_(["pending", "assigned", "in_progress"]))
    ).subquery()

    # totals by status
    totals_q = select(
        func.sum(sa.case((base.c.status == "pending", 1), else_=0)).label("total_pending"),
        func.sum(sa.case((base.c.status == "assigned", 1), else_=0)).label("total_assigned"),
        func.sum(sa.case((base.c.status == "in_progress", 1), else_=0)).label("total_in_progress"),
        func.sum(sa.case((sa.and_(base.c.sla_deadline > now, base.c.sla_deadline <= approaching_cutoff), 1), else_=0)).label(
            "approaching_sla"
        ),
        func.sum(sa.case((base.c.sla_deadline <= now, 1), else_=0)).label("breached_sla"),
    )

    totals = (await session.execute(totals_q)).mappings().one()

    # priority buckets
    by_priority_q = select(base.c.priority)
    priorities = [int(r[0]) for r in (await session.execute(by_priority_q)).all()]
    buckets = {"high": 0, "medium": 0, "low": 0}
    for p in priorities:
        buckets[_priority_bucket(p)] += 1

    return {
        "total_pending": int(totals["total_pending"] or 0),
        "total_assigned": int(totals["total_assigned"] or 0),
        "total_in_progress": int(totals["total_in_progress"] or 0),
        "approaching_sla": int(totals["approaching_sla"] or 0),
        "breached_sla": int(totals["breached_sla"] or 0),
        "by_priority": buckets,
    }
