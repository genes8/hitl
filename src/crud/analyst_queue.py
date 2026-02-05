from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.analyst_queue import AnalystQueue


async def get_latest_queue_entry_for_application(
    session: AsyncSession,
    *,
    application_id,
) -> AnalystQueue | None:
    stmt = (
        select(AnalystQueue)
        .where(AnalystQueue.application_id == application_id)
        .order_by(AnalystQueue.created_at.desc())
        .limit(1)
    )

    res = await session.execute(stmt)
    return res.scalar_one_or_none()
