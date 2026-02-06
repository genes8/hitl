from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud import BaseCRUD
from src.crud.application import create_application
from src.database import get_db
from src.models.application import Application
from src.models.scoring_result import ScoringResult
from src.schemas.application import ApplicationCreate, ApplicationRead
from src.schemas.scoring_result import ScoringResultRead


router = APIRouter(prefix="/applications", tags=["applications"])

application_crud = BaseCRUD[Application, ApplicationCreate, ApplicationCreate](Application)


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application_endpoint(
    application_id: UUID,
    tenant_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    """Fetch application by id.

    Optional tenant scoping supports multi-tenancy isolation until auth is wired.
    """

    app = await application_crud.get(session=session, id=application_id, tenant_id=tenant_id)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")

    app_read = ApplicationRead.model_validate(app)

    scoring_stmt = (
        select(ScoringResult)
        .where(ScoringResult.application_id == application_id)
        .order_by(ScoringResult.created_at.desc())
        .limit(1)
    )
    scoring_result = (await session.execute(scoring_stmt)).scalar_one_or_none()
    if scoring_result is not None:
        app_read.scoring_result = ScoringResultRead.model_validate(scoring_result)

    return app_read


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def create_application_endpoint(
    payload: ApplicationCreate,
    session: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    app = await create_application(session=session, obj_in=payload)

    # TODO-2.1.1: Emit Celery task score_application(app.id)
    # Placeholder until Celery wiring lands.

    return ApplicationRead.model_validate(app)
