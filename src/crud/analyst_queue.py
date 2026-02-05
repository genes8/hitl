from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.analyst_queue import AnalystQueue


async def get_latest_queue_entry_for_application(
    session: AsyncSession,
    *,
    application_id: UUID,
) -> AnalystQueue | None:
    stmt = (
        select(AnalystQueue)
        .where(AnalystQueue.application_id == application_id)
        .order_by(desc(AnalystQueue.created_at))
        .limit(1)
    )

    res = await session.execute(stmt)
    return res.scalar_one_or_none()
