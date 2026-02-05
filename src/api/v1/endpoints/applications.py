from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.analyst_queue import get_latest_queue_entry_for_application
from src.crud.application import create_application, get_application
from src.crud.decision import list_decisions_for_application
from src.crud.scoring_result import get_latest_scoring_result_for_application
from src.crud.similar_case import list_similar_cases_for_application
from src.database import get_db
from src.schemas.application import ApplicationCreate, ApplicationRead


router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def create_application_endpoint(
    payload: ApplicationCreate,
    session: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    app = await create_application(session=session, obj_in=payload)

    # TODO-2.1.1: Emit Celery task score_application(app.id)
    # Placeholder until Celery wiring lands.

    return ApplicationRead.model_validate(app)


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application_endpoint(
    application_id: UUID,
    tenant_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    app = await get_application(
        session=session,
        application_id=application_id,
        tenant_id=tenant_id,
    )

    if app is None:
        raise HTTPException(status_code=404, detail="application not found")

    scoring = await get_latest_scoring_result_for_application(session, application_id=app.id)
    queue_entry = await get_latest_queue_entry_for_application(session, application_id=app.id)
    decisions = await list_decisions_for_application(session, application_id=app.id)
    similar_cases = await list_similar_cases_for_application(session, application_id=app.id)

    # Attach dynamically so the existing Application model doesn't need ORM relationships yet.
    setattr(app, "scoring_result", scoring)
    setattr(app, "queue_info", queue_entry)
    setattr(app, "decision_history", decisions)
    setattr(app, "similar_cases", similar_cases)

    return ApplicationRead.model_validate(app)
