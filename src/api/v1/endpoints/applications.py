from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.application import (
    create_application,
    get_application,
    get_latest_scoring_result,
    list_applications,
)
from src.database import get_db
from src.schemas.application import (
    ApplicationCreate,
    ApplicationListItem,
    ApplicationListResponse,
    ApplicationRead,
)
from src.schemas.scoring_result import ScoringResultRead


router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def create_application_endpoint(
    payload: ApplicationCreate,
    session: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    app = await create_application(session=session, obj_in=payload)

    # TODO-2.1.1: Emit Celery task score_application(app.id)
    # We call a small dispatcher shim so we don't need Celery installed until
    # TODO-2.4.1 lands.
    from src.worker.dispatch import enqueue_score_application

    enqueue_score_application(application_id=app.id)

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
    cursor: str | None = Query(None, description="Cursor for pagination: <created_at_iso>|<id>"),
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

    parsed_cursor = None
    if cursor is not None:
        try:
            import uuid

            created_at_raw, app_id_raw = cursor.split("|", 1)
            cursor_dt = datetime.fromisoformat(created_at_raw)
            cursor_id = uuid.UUID(app_id_raw)
            parsed_cursor = (cursor_dt, cursor_id)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=422, detail="Invalid cursor") from e

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
            cursor=parsed_cursor,
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

    payload = ApplicationRead.model_validate(app).model_dump()
    payload["scoring_result"] = ScoringResultRead.model_validate(scoring).model_dump() if scoring else None

    return ApplicationRead(**payload)
