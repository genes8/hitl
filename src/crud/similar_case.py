from __future__ import annotations

import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.similar_case import SimilarCase


async def get_similar_cases_for_application(
    *,
    session: AsyncSession,
    application_id: uuid.UUID,
    limit: int = 10,
) -> list[SimilarCase]:
    stmt = (
        select(SimilarCase)
        .where(SimilarCase.application_id == application_id)
        .order_by(desc(SimilarCase.match_score), desc(SimilarCase.created_at))
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
