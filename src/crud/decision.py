from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.decision import Decision


async def list_decisions_for_application(
    session: AsyncSession,
    *,
    application_id,
    limit: int = 50,
) -> list[Decision]:
    """Return decisions for an application (newest first).

    Kept intentionally small for application detail use-cases.
    """

    stmt = (
        select(Decision)
        .where(Decision.application_id == application_id)
        .order_by(Decision.created_at.desc())
        .limit(limit)
    )

    res = await session.execute(stmt)
    return list(res.scalars().all())
