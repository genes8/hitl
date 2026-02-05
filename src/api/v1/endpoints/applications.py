from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.application import create_application, get_application, list_applications
from src.database import get_db
from src.schemas.application import (
    ApplicationCreate,
    ApplicationListItem,
    ApplicationListResponse,
    ApplicationRead,
)


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
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> ApplicationListResponse:
    import uuid

    try:
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid tenant_id")

    items, total = await list_applications(
        session=session,
        tenant_id=tenant_uuid,
        status=status,
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
    session: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    try:
        # FastAPI will accept UUID directly, but keep it explicit to get a clean 404
        # rather than a 422 for malformed UUIDs later.
        import uuid

        app_id = uuid.UUID(application_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Application not found")

    app = await get_application(session=session, application_id=app_id)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")

    return ApplicationRead.model_validate(app)
