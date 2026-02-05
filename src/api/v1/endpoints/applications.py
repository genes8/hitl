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
    update_application,
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
    sort_by: str = Query("created_at", description="Sort field: created_at | amount | score"),
    sort_order: str = Query("desc", description="Sort order: asc | desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> ApplicationListResponse:
    import uuid

    try:
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid tenant_id")

    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be <= to_date")

    if sort_by not in {"created_at", "amount", "score"}:
        raise HTTPException(status_code=422, detail="Invalid sort_by")

    if sort_order not in {"asc", "desc"}:
        raise HTTPException(status_code=422, detail="Invalid sort_order")

    items, total = await list_applications(
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
    )

    return ApplicationListResponse(
        items=[ApplicationListItem.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
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
async def update_application_endpoint(
    application_id: str,
    payload: ApplicationUpdate,
    tenant_id: str | None = Query(None, description="Optional tenant UUID to enforce isolation"),
    session: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    import uuid

    try:
        app_id = uuid.UUID(application_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Application not found")

    tenant_uuid = None
    if tenant_id is not None:
        try:
            tenant_uuid = uuid.UUID(tenant_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid tenant_id")

    # Fetch first to allow clear status-based errors.
    app = await get_application(session=session, application_id=app_id, tenant_id=tenant_uuid)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.status != "pending":
        raise HTTPException(status_code=409, detail="Application cannot be updated")

    updated = await update_application(
        session=session,
        application_id=app_id,
        tenant_id=tenant_uuid,
        obj_in=payload,
    )

    # Should only happen if the record vanished between calls.
    if updated is None:
        raise HTTPException(status_code=404, detail="Application not found")

    if payload.status is not None and payload.status != "cancelled" and updated.status == "pending":
        raise HTTPException(status_code=409, detail="Invalid status transition")

    scoring = await get_latest_scoring_result(session=session, application_id=updated.id)
    queue_entry = await get_latest_queue_entry(session=session, application_id=updated.id)
    decisions = await list_decisions(session=session, application_id=updated.id)
    similar_cases = await list_similar_cases(session=session, application_id=updated.id)

    resp = ApplicationRead.model_validate(updated).model_dump()
    resp["scoring_result"] = ScoringResultRead.model_validate(scoring).model_dump() if scoring else None
    resp["queue_info"] = AnalystQueueRead.model_validate(queue_entry).model_dump() if queue_entry else None
    resp["decision_history"] = [DecisionRead.model_validate(d).model_dump() for d in decisions]
    resp["similar_cases"] = [SimilarCaseRead.model_validate(s).model_dump() for s in similar_cases]

    return ApplicationRead(**resp)


@router.delete("/{application_id}", response_model=ApplicationRead)
async def cancel_application_endpoint(
    application_id: str,
    tenant_id: str | None = Query(None, description="Optional tenant UUID to enforce isolation"),
    session: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    import uuid

    try:
        app_id = uuid.UUID(application_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Application not found")

    tenant_uuid = None
    if tenant_id is not None:
        try:
            tenant_uuid = uuid.UUID(tenant_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid tenant_id")

    app = await cancel_application(session=session, application_id=app_id, tenant_id=tenant_uuid)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.status != "cancelled":
        # Only pending applications can be cancelled in v1.
        raise HTTPException(status_code=409, detail="Application cannot be cancelled")

    # Reuse detail serialization so the response stays consistent.
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
