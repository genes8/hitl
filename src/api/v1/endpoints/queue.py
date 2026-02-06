from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.queue import list_queue_entries, queue_summary
from src.database import get_db
from src.schemas.analyst_queue import (
    AnalystQueueListResponse,
    AnalystQueueRead,
    AnalystQueueSummaryResponse,
)

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("", response_model=AnalystQueueListResponse)
async def list_queue_endpoint(
    tenant_id: str = Query(..., description="Tenant UUID"),
    status: str | None = Query(None, description="pending | assigned | in_progress"),
    analyst_id: str | None = Query(None, description="Optional analyst UUID"),
    priority_max: int | None = Query(None, ge=1, le=100),
    sort_by: str = Query("priority", description="priority | created_at | sla_deadline"),
    sort_order: str = Query("asc", description="asc | desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> AnalystQueueListResponse:
    import uuid

    try:
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid tenant_id")

    analyst_uuid = None
    if analyst_id is not None:
        try:
            analyst_uuid = uuid.UUID(analyst_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid analyst_id")

    if status is not None and status not in {"pending", "assigned", "in_progress"}:
        raise HTTPException(status_code=422, detail="Invalid status")

    if sort_by not in {"priority", "created_at", "sla_deadline"}:
        raise HTTPException(status_code=422, detail="Invalid sort_by")

    if sort_order not in {"asc", "desc"}:
        raise HTTPException(status_code=422, detail="Invalid sort_order")

    items = await list_queue_entries(
        session=session,
        tenant_id=tenant_uuid,
        status=status,
        analyst_id=analyst_uuid,
        priority_max=priority_max,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )

    return AnalystQueueListResponse(items=[AnalystQueueRead.model_validate(i) for i in items])


@router.get("/summary", response_model=AnalystQueueSummaryResponse)
async def queue_summary_endpoint(
    tenant_id: str = Query(..., description="Tenant UUID"),
    session: AsyncSession = Depends(get_db),
) -> AnalystQueueSummaryResponse:
    import uuid

    try:
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid tenant_id")

    payload = await queue_summary(session=session, tenant_id=tenant_uuid)
    return AnalystQueueSummaryResponse(**payload)
