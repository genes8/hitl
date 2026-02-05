from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.analyst_queue import get_latest_queue_entry_for_application
from src.crud.application import create_application, get_application
from src.crud.decision import get_decisions_for_application
from src.crud.scoring_result import get_latest_scoring_result_for_application
from src.database import get_db
from src.schemas.analyst_queue import AnalystQueueRead
from src.schemas.application import ApplicationCreate, ApplicationRead
from src.schemas.decision import DecisionRead
from src.schemas.scoring_result import ScoringResultRead


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
    tenant_id: UUID | None = None,
    session: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    app = await get_application(session=session, application_id=application_id, tenant_id=tenant_id)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")

    scoring = await get_latest_scoring_result_for_application(session=session, application_id=app.id)
    queue_entry = await get_latest_queue_entry_for_application(session=session, application_id=app.id)
    decisions = await get_decisions_for_application(session=session, application_id=app.id)

    out = ApplicationRead.model_validate(app)
    out.scoring_result = ScoringResultRead.model_validate(scoring) if scoring is not None else None
    out.queue_entry = AnalystQueueRead.model_validate(queue_entry) if queue_entry is not None else None
    out.decision_history = [DecisionRead.model_validate(d) for d in decisions]
    return out
