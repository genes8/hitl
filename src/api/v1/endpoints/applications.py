from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.application import (
    create_application,
    get_application,
    get_decision_history,
    get_latest_queue_entry,
    get_latest_scoring_result,
    get_similar_cases,
    list_applications,
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
from src.schemas.decision import DecisionRead
from src.schemas.queue import QueueInfoRead
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
    # Best-effort enqueue: the create call should still succeed even if Redis/Celery is down.
    from src.worker.tasks import score_application

    try:
        score_application.delay(str(app.id))
    except Exception:
        import logging

        logging.getLogger(__name__).exception(
            "Failed to enqueue score_application task",
            extra={"application_id": str(app.id)},
        )

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
    cursor: str | None = Query(
        None,
        description=(
            "Optional cursor for pagination. Only supported with sort_by=created_at. "
            "Use the next_cursor value from the previous response."
        ),
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

    if sort_by not in {"created_at", "amount", "score"}:
        raise HTTPException(status_code=422, detail="Invalid sort_by")

    if sort_order not in {"asc", "desc"}:
        raise HTTPException(status_code=422, detail="Invalid sort_order")

    if cursor is not None and sort_by != "created_at":
        raise HTTPException(
            status_code=422,
            detail="cursor pagination is only supported with sort_by=created_at",
        )

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

    return ApplicationListResponse(
        items=[ApplicationListItem.model_validate(i) for i in items],
        total=total,
        page=1 if cursor is not None else page,
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
    decisions = await get_decision_history(session=session, application_id=app.id)
    similar_cases = await get_similar_cases(session=session, application_id=app.id)

    payload = ApplicationRead.model_validate(app).model_dump()
    payload["scoring_result"] = ScoringResultRead.model_validate(scoring).model_dump() if scoring else None
    payload["queue_info"] = QueueInfoRead.model_validate(queue_entry).model_dump() if queue_entry else None
    payload["decision_history"] = [DecisionRead.model_validate(d).model_dump() for d in decisions]
    payload["similar_cases"] = [SimilarCaseRead.model_validate(s).model_dump() for s in similar_cases]

    return ApplicationRead(**payload)


@router.patch("/{application_id}", response_model=ApplicationRead)
async def patch_application_endpoint(
    application_id: str,
    payload: ApplicationUpdate,
    internal: bool = Query(
        False,
        description=(
            "Allow internal-only status transitions (temporary; will be replaced by auth)."
        ),
    ),
    session: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    import uuid

    try:
        app_id = uuid.UUID(application_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Application not found")

    app = await get_application(session=session, application_id=app_id)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")

    update_data = payload.model_dump(exclude_unset=True)

    # Field updates are only allowed while the application is pending.
    field_keys = {
        "external_id",
        "applicant_data",
        "financial_data",
        "loan_request",
        "credit_bureau_data",
        "source",
    }
    has_field_updates = any(k in update_data for k in field_keys)

    if has_field_updates and app.status != "pending":
        raise HTTPException(
            status_code=422,
            detail="Only pending applications can be edited",
        )

    # Status transition validation.
    new_status = update_data.get("status")
    if new_status is not None:
        old_status = app.status

        allowed_public = {
            ("pending", "cancelled"),
            ("review", "approved"),
            ("review", "declined"),
        }
        allowed_internal = {
            ("pending", "scoring"),
            ("scoring", "review"),
            ("scoring", "approved"),
            ("scoring", "declined"),
        }

        if (old_status, new_status) in allowed_public:
            pass
        elif (old_status, new_status) in allowed_internal:
            if not internal:
                raise HTTPException(
                    status_code=403,
                    detail="Status transition is internal-only",
                )
        else:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status transition: {old_status} -> {new_status}",
            )

    updated = await update_application(session=session, db_obj=app, obj_in=payload)
    return ApplicationRead.model_validate(updated)


@router.delete("/{application_id}", response_model=ApplicationRead)
async def cancel_application_endpoint(
    application_id: str,
    session: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    """Cancel an application (soft-delete).

    Spec (hitl/todo.md TODO-2.1.3): DELETE /applications/{id} sets status=cancelled.
    """
    import uuid

    try:
        app_id = uuid.UUID(application_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Application not found")

    app = await get_application(session=session, application_id=app_id)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.status == "cancelled":
        return ApplicationRead.model_validate(app)

    if app.status != "pending":
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status transition: {app.status} -> cancelled",
        )

    updated = await update_application(
        session=session,
        db_obj=app,
        obj_in=ApplicationUpdate(status="cancelled"),
    )
    return ApplicationRead.model_validate(updated)
