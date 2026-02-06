from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.application import Application
from src.models.audit_log import AuditLog
from src.models.scoring_result import ScoringResult
from src.schemas.application import ApplicationCreate


def _compute_derived(financial_data: dict, loan_request: dict) -> dict:
    # Spec (hitl/todo.md):
    # dti_ratio = (monthly_obligations + existing_loans_payment) / net_monthly_income
    # loan_to_income = loan_amount / (net_monthly_income * 12)
    # payment_to_income = estimated_payment / net_monthly_income
    net_income = float(financial_data.get("net_monthly_income", 0) or 0)
    monthly_obligations = float(financial_data.get("monthly_obligations", 0) or 0)
    existing_loans_payment = float(financial_data.get("existing_loans_payment", 0) or 0)
    loan_amount = float(loan_request.get("loan_amount", 0) or 0)
    estimated_payment = float(loan_request.get("estimated_payment", 0) or 0)

    if net_income <= 0:
        # Avoid division by zero. Keep ratios None if we cannot compute.
        return {
            "dti_ratio": None,
            "loan_to_income": None,
            "payment_to_income": None,
        }

    return {
        "dti_ratio": (monthly_obligations + existing_loans_payment) / net_income,
        "loan_to_income": loan_amount / (net_income * 12.0),
        "payment_to_income": estimated_payment / net_income,
    }


async def get_application(
    session: AsyncSession,
    *,
    application_id,
    tenant_id=None,
) -> Application | None:
    q = select(Application).where(Application.id == application_id)
    if tenant_id is not None:
        q = q.where(Application.tenant_id == tenant_id)

    r = await session.execute(q)
    return r.scalar_one_or_none()


async def get_latest_scoring_result(
    session: AsyncSession,
    *,
    application_id,
) -> ScoringResult | None:
    q = (
        select(ScoringResult)
        .where(ScoringResult.application_id == application_id)
        .order_by(ScoringResult.created_at.desc())
        .limit(1)
    )
    r = await session.execute(q)
    return r.scalar_one_or_none()


async def list_applications(
    session: AsyncSession,
    *,
    tenant_id,
    status: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
    cursor: str | None = None,
) -> tuple[list[Application], int, str | None]:
    # Phase 2.1.2 (minimal): listing + status filter + simple pagination.
    # Tenant id is required until auth/tenant-context middleware lands.
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100

    def _encode_cursor(created_at: datetime, app_id: UUID) -> str:
        raw = f"{created_at.isoformat()}|{app_id}".encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii")

    def _decode_cursor(value: str) -> tuple[datetime, UUID]:
        try:
            raw = base64.urlsafe_b64decode(value.encode("ascii")).decode("utf-8")
            created_at_s, app_id_s = raw.split("|", 1)
            created_at = datetime.fromisoformat(created_at_s)
            app_id = UUID(app_id_s)
        except Exception as e:  # noqa: BLE001
            raise ValueError("Invalid cursor") from e

        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return created_at, app_id

    cursor_created_at: datetime | None = None
    cursor_id: UUID | None = None
    if cursor is not None:
        cursor_created_at, cursor_id = _decode_cursor(cursor)

    base = select(Application).where(Application.tenant_id == tenant_id)

    score_subq = None
    if sort_by == "score":
        # There may be multiple scoring results over time; list view sorts by the
        # latest/highest score we have for the application (v0: max(score)).
        score_subq = (
            select(
                ScoringResult.application_id.label("app_id"),
                func.max(ScoringResult.score).label("score"),
            )
            .group_by(ScoringResult.application_id)
            .subquery()
        )
        base = base.outerjoin(score_subq, score_subq.c.app_id == Application.id)
    if status:
        base = base.where(Application.status == status)

    if search:
        s = f"%{search.strip()}%"
        base = base.where(
            (Application.external_id.ilike(s))
            | (Application.applicant_data["name"].astext.ilike(s))
        )

    # If caller provided naive datetimes, assume UTC.
    if from_date is not None and from_date.tzinfo is None:
        from_date = from_date.replace(tzinfo=timezone.utc)
    if to_date is not None and to_date.tzinfo is None:
        to_date = to_date.replace(tzinfo=timezone.utc)

    if from_date is not None:
        base = base.where(Application.created_at >= from_date)
    if to_date is not None:
        base = base.where(Application.created_at <= to_date)

    # total count
    count_q = select(func.count()).select_from(base.subquery())
    total = int((await session.execute(count_q)).scalar_one())

    # Ordering
    order_expr = None
    if sort_by == "created_at":
        order_expr = Application.created_at
    elif sort_by == "amount":
        # loan_request is JSONB; cast loan_amount to numeric for sorting.
        order_expr = Application.loan_request["loan_amount"].astext.cast(sa.Numeric)
    elif sort_by == "score":
        # Joined via score_subq above.
        order_expr = (score_subq.c.score if score_subq is not None else None)
    else:
        order_expr = Application.created_at

    if order_expr is None:
        order_expr = Application.created_at

    if sort_order == "asc":
        order_expr = sa.nulls_last(order_expr.asc())
    else:
        order_expr = sa.nulls_last(order_expr.desc())

    # Always add a stable tie-breaker to ensure deterministic pagination.
    if sort_order == "asc":
        id_order = Application.id.asc()
    else:
        id_order = Application.id.desc()

    if cursor is not None and sort_by == "created_at" and cursor_created_at is not None and cursor_id is not None:
        # Cursor paging is only defined for created_at ordering.
        if sort_order == "asc":
            base = base.where(
                sa.or_(
                    Application.created_at > cursor_created_at,
                    sa.and_(
                        Application.created_at == cursor_created_at,
                        Application.id > cursor_id,
                    ),
                )
            )
        else:
            base = base.where(
                sa.or_(
                    Application.created_at < cursor_created_at,
                    sa.and_(
                        Application.created_at == cursor_created_at,
                        Application.id < cursor_id,
                    ),
                )
            )

        q = base.order_by(order_expr, id_order).limit(page_size)
        items = (await session.execute(q)).scalars().all()

        next_cursor = None
        if len(items) == page_size:
            last = items[-1]
            next_cursor = _encode_cursor(last.created_at, last.id)

        return items, total, next_cursor

    q = base.order_by(order_expr, id_order).offset((page - 1) * page_size).limit(page_size)
    items = (await session.execute(q)).scalars().all()

    next_cursor = None
    if sort_by == "created_at" and len(items) == page_size:
        last = items[-1]
        next_cursor = _encode_cursor(last.created_at, last.id)

    return items, total, next_cursor


async def create_application(session: AsyncSession, obj_in: ApplicationCreate) -> Application:
    external_id = obj_in.external_id or f"APP-{uuid4().hex[:10]}"

    expires_at = datetime.now(timezone.utc) + timedelta(days=30)

    derived = _compute_derived(obj_in.financial_data, obj_in.loan_request)

    app = Application(
        tenant_id=obj_in.tenant_id,
        external_id=external_id,
        status="pending",
        applicant_data=obj_in.applicant_data,
        financial_data=obj_in.financial_data,
        loan_request=obj_in.loan_request,
        credit_bureau_data=obj_in.credit_bureau_data,
        source=obj_in.source,
        meta={"derived": derived},
        expires_at=expires_at,
    )

    session.add(app)
    await session.flush()  # ensure app.id is available

    audit = AuditLog(
        tenant_id=obj_in.tenant_id,
        user_id=None,
        entity_type="application",
        entity_id=app.id,
        action="create",
        old_value=None,
        new_value={
            "external_id": external_id,
            "status": "pending",
            "source": obj_in.source,
            "meta": {"derived": derived},
        },
        change_summary="application created",
    )
    session.add(audit)

    await session.commit()
    await session.refresh(app)
    return app
