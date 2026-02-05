from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.decision import Decision


async def get_decisions_for_application(
    session: AsyncSession,
    *,
    application_id: UUID,
) -> list[Decision]:
    stmt = select(Decision).where(Decision.application_id == application_id).order_by(Decision.created_at.asc())
    res = await session.execute(stmt)
    return list(res.scalalars().all())
