from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Numeric, String, cast, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud import BaseCRUD
from src.crud.application import create_application
from src.database import get_db
from src.models.application import Application
from src.models.scoring_result import ScoringResult
from src.schemas.application import ApplicationCreate, ApplicationListResponse, ApplicationRead
from src.schemas.scoring_result import ScoringResultRead


router = APIRouter(prefix="/applications", tags=["applications"])

application_crud = BaseCRUD[Application, ApplicationCreate, ApplicationCreate](Application)


@router.get("", response_model=ApplicationListResponse)
async def list_applications_endpoint(
    tenant_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    search: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> ApplicationListResponse:
    """List applications with basic filtering and pagination."""

    filters: list[object] = []

    if tenant_id is not None:
        filters.append(Application.tenant_id == tenant_id)

    if status is not None:
        filters.append(Application.status == status)

    # submitted_at is the domain timestamp; created_at is DB insertion time.
    if from_date is not None:
        filters.append(Application.submitted_at >= from_date)
    if to_date is not None:
        filters.append(Application.submitted_at <= to_date)

    if search:
        like = f"%{search}%"
        filters.append(
            or_(
                cast(Application.external_id, String).ilike(like),
                cast(Application.applicant_data, String).ilike(like),
            )
        )

    if sort_by not in {"created_at", "submitted_at", "amount"}:
        raise HTTPException(status_code=400, detail="Invalid sort_by")
    if sort_order not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="Invalid sort_order")

    if sort_by == "created_at":
        sort_col = Application.created_at
    elif sort_by == "submitted_at":
        sort_col = Application.submitted_at
    else:
        # Best-effort sorting by JSON loan_amount.
        sort_col = cast(Application.loan_request["loan_amount"].astext, Numeric)

    order_expr = sort_col if sort_order == "asc" else desc(sort_col)

    count_stmt = select(func.count()).select_from(Application)
    for f in filters:
        count_stmt = count_stmt.where(f)
    total = int((await session.execute(count_stmt)).scalar_one())

    offset = (page - 1) * page_size

    stmt = select(Application)
    for f in filters:
        stmt = stmt.where(f)

    stmt = stmt.order_by(order_expr).offset(offset).limit(page_size)

    rows = (await session.execute(stmt)).scalars().all()
    items = [ApplicationRead.model_validate(a) for a in rows]

    return ApplicationListResponse(items=items, total=total, page=page, page_size=page_size)


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
