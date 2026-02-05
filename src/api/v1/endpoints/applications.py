from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.application import create_application, get_application, get_latest_scoring_result
from src.database import get_db
from src.schemas.application import ApplicationCreate, ApplicationRead
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
