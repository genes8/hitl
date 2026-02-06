from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.decision import Decision


async def get_decisions_for_application(
    session: AsyncSession,
    *,
    application_id,
) -> list[Decision]:
    q = (
        select(Decision)
        .where(Decision.application_id == application_id)
        .order_by(Decision.created_at.asc(), Decision.id.asc())
    )
    r = await session.execute(q)
    return list(r.scalars().all())
