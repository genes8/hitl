from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.application import (
    cancel_application,
    create_application,
    get_application,
    get_latest_queue_entry,
    get_latest_scoring_result,
    list_applications,
    list_decisions,
    list_similar_cases,
    update_application_pending,
)
from src.database import get_db
from src.schemas.application import (
    ApplicationCreate,
    ApplicationListItem,
    ApplicationListResponse,
    ApplicationRead,
    ApplicationUpdate,
)
from src.schemas.analyst_queue import AnalystQueueRead
from src.schemas.decision import DecisionRead
from src.schemas.scoring_result import ScoringResultRead
from src.schemas.similar_case import SimilarCaseRead


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


@router.get("", response_model=ApplicationListResponse)
async def list_applications_endpoint(
    tenant_id: str = Query(..., description="Tenant UUID"),
    status: str | None = Query(None, description="Application status"),
    from_date: datetime | None = Query(None, description="Filter: created_at >= from_date"),
    to_date: datetime | None = Query(None, description="Filter: created_at <= to_date"),
    search: str | None = Query(None, description="Search: external_id or applicant name"),
    sort_by: str = Query(
        "created_at",
        description="Sort field: created_at | submitted_at | amount | score",
    ),
    sort_order: str = Query("desc", description="Sort order: asc | desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(
        None,
        description="Optional cursor for keyset pagination (only for created_at/submitted_at)",
    ),
    session: AsyncSession = Depends(get_db),
) -> ApplicationListResponse:
    import uuid

    try:
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid tenant_id")

    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be <= to_date")

    if sort_by not in {"created_at", "submitted_at", "amount", "score"}:
        raise HTTPException(status_code=422, detail="Invalid sort_by")

    if sort_order not in {"asc", "desc"}:
        raise HTTPException(status_code=422, detail="Invalid sort_order")

    if cursor is not None and sort_by not in {"created_at", "submitted_at"}:
        raise HTTPException(
            status_code=422,
            detail="cursor pagination is only supported for sort_by=created_at|submitted_at",
        )

    try:
        items, total, next_cursor = await list_applications(
            session=session,
            tenant_id=tenant_uuid,
            status=status,
            from_date=from_date,
            to_date=to_date,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
            cursor=cursor,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    return ApplicationListResponse(
        items=[ApplicationListItem.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        next_cursor=next_cursor,
    )


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application_endpoint(
    application_id: str,
    tenant_id: str | None = Query(None, description="Optional tenant UUID to enforce isolation"),
    session: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    import uuid

    try:
        # Keep it explicit to get a clean 404 for malformed UUIDs.
        app_id = uuid.UUID(application_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Application not found")

    tenant_uuid = None
    if tenant_id is not None:
        try:
            tenant_uuid = uuid.UUID(tenant_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid tenant_id")

    app = await get_application(session=session, application_id=app_id, tenant_id=tenant_uuid)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")

    scoring = await get_latest_scoring_result(session=session, application_id=app.id)
    queue_entry = await get_latest_queue_entry(session=session, application_id=app.id)
    decisions = await list_decisions(session=session, application_id=app.id)
    similar_cases = await list_similar_cases(session=session, application_id=app.id)

    payload = ApplicationRead.model_validate(app).model_dump()
    payload["scoring_result"] = ScoringResultRead.model_validate(scoring).model_dump() if scoring else None
    payload["queue_info"] = AnalystQueueRead.model_validate(queue_entry).model_dump() if queue_entry else None
    payload["decision_history"] = [DecisionRead.model_validate(d).model_dump() for d in decisions]
    payload["similar_cases"] = [SimilarCaseRead.model_validate(s).model_dump() for s in similar_cases]

    return ApplicationRead(**payload)


@router.patch("/{application_id}", response_model=ApplicationRead)
async def patch_application_endpoint(
    application_id: str,
    payload: ApplicationUpdate,
    tenant_id: str = Query(..., description="Tenant UUID"),
    session: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    """Update a pending application or cancel it.

    v1 constraints:
    - Field updates only allowed while status=pending.
    - Status transition supported: pending -> cancelled.
    """

    import uuid

    try:
        app_id = uuid.UUID(application_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Application not found")

    try:
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid tenant_id")

    app = await get_application(session=session, application_id=app_id, tenant_id=tenant_uuid)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")

    # Status transition (limited).
    if payload.status is not None:
        if payload.status != "cancelled":
            raise HTTPException(status_code=422, detail="Only status=cancelled is supported")
        try:
            app = await cancel_application(session=session, app=app)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    # Field updates.
    has_field_updates = any(
        v is not None
        for v in (
            payload.external_id,
            payload.applicant_data,
            payload.financial_data,
            payload.loan_request,
            payload.credit_bureau_data,
        )
    )

    if has_field_updates:
        try:
            app = await update_application_pending(
                session=session,
                app=app,
                external_id=payload.external_id,
                applicant_data=payload.applicant_data,
                financial_data=payload.financial_data,
                loan_request=payload.loan_request,
                credit_bureau_data=payload.credit_bureau_data,
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    return ApplicationRead.model_validate(app)


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application_endpoint(
    application_id: str,
    tenant_id: str = Query(..., description="Tenant UUID"),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete (cancel) a pending application by setting status=cancelled."""

    import uuid

    try:
        app_id = uuid.UUID(application_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Application not found")

    try:
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid tenant_id")

    app = await get_application(session=session, application_id=app_id, tenant_id=tenant_uuid)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")

    try:
        await cancel_application(session=session, app=app)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    return None
