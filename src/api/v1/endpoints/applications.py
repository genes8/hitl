from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.analyst_queue import get_latest_queue_entry_for_application
from src.crud.application import create_application, get_application, update_application
from src.crud.decision import list_decisions_for_application
from src.crud.scoring_result import get_latest_scoring_result_for_application
from src.crud.similar_case import list_similar_cases_for_application
from src.database import get_db
from src.schemas.application import ApplicationCreate, ApplicationRead, ApplicationUpdate


router = APIRouter(prefix="/applications", tags=["applications"])


_ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"cancelled", "scoring"},
    "scoring": {"review", "approved", "declined"},
    "review": {"approved", "declined"},
}


def _validate_status_transition(*, from_status: str, to_status: str) -> None:
    if from_status == to_status:
        return

    allowed = _ALLOWED_STATUS_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid status transition: {from_status} -> {to_status}",
        )


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


@router.patch("/{application_id}", response_model=ApplicationRead)
async def patch_application_endpoint(
    application_id: UUID,
    payload: ApplicationUpdate,
    tenant_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    app = await get_application(session=session, application_id=application_id, tenant_id=tenant_id)

    if app is None:
        raise HTTPException(status_code=404, detail="application not found")

    # Status transition validation (TODO-2.1.3).
    if payload.status is not None:
        _validate_status_transition(from_status=app.status, to_status=payload.status)

        # Internal-only transitions are not enforced until auth/roles land.
        # (See hitl/todo.md TODO-1.2.*)

    # Field updates are allowed only while the application is pending.
    field_update_attempt = any(
        v is not None
        for v in (
            payload.external_id,
            payload.applicant_data,
            payload.financial_data,
            payload.loan_request,
            payload.credit_bureau_data,
            payload.source,
        )
    )

    if field_update_attempt and app.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="field updates are only allowed for pending applications",
        )

    app = await update_application(session=session, app=app, obj_in=payload)

    # Reuse the same response shape as GET /applications/{id}.
    scoring = await get_latest_scoring_result_for_application(session, application_id=app.id)
    queue_entry = await get_latest_queue_entry_for_application(session, application_id=app.id)
    decisions = await list_decisions_for_application(session, application_id=app.id)
    similar_cases = await list_similar_cases_for_application(session, application_id=app.id)

    setattr(app, "scoring_result", scoring)
    setattr(app, "queue_info", queue_entry)
    setattr(app, "decision_history", decisions)
    setattr(app, "similar_cases", similar_cases)

    return ApplicationRead.model_validate(app)


@router.delete("/{application_id}", response_model=ApplicationRead)
async def delete_application_endpoint(
    application_id: UUID,
    tenant_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    app = await get_application(session=session, application_id=application_id, tenant_id=tenant_id)

    if app is None:
        raise HTTPException(status_code=404, detail="application not found")

    # Spec: DELETE sets status = cancelled (pending -> cancelled only).
    _validate_status_transition(from_status=app.status, to_status="cancelled")

    app = await update_application(session=session, app=app, obj_in=ApplicationUpdate(status="cancelled"))

    scoring = await get_latest_scoring_result_for_application(session, application_id=app.id)
    queue_entry = await get_latest_queue_entry_for_application(session, application_id=app.id)
    decisions = await list_decisions_for_application(session, application_id=app.id)
    similar_cases = await list_similar_cases_for_application(session, application_id=app.id)

    setattr(app, "scoring_result", scoring)
    setattr(app, "queue_info", queue_entry)
    setattr(app, "decision_history", decisions)
    setattr(app, "similar_cases", similar_cases)

    return ApplicationRead.model_validate(app)
