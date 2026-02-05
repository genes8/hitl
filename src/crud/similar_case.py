from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.similar_case import SimilarCase


async def list_similar_cases_for_application(
    session: AsyncSession,
    *,
    application_id: UUID,
    limit: int = 10,
) -> list[SimilarCase]:
    result = await session.execute(
        select(SimilarCase)
        .where(SimilarCase.application_id == application_id)
        .order_by(desc(SimilarCase.match_score), desc(SimilarCase.created_at))
        .limit(limit)
    )

    return list(result.scalars().all())
