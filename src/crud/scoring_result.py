from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.scoring_result import ScoringResult


async def get_latest_scoring_result_for_application(
    session: AsyncSession,
    *,
    application_id: UUID,
) -> ScoringResult | None:
    stmt = (
        select(ScoringResult)
        .where(ScoringResult.application_id == application_id)
        .order_by(desc(ScoringResult.created_at))
        .limit(1)
    )

    res = await session.execute(stmt)
    return res.scalar_one_or_none()
