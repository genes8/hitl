from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import base64
import json

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.analyst_queue import AnalystQueue
from src.models.application import Application
from src.models.audit_log import AuditLog
from src.models.decision import Decision
from src.models.scoring_result import ScoringResult
from src.models.similar_case import SimilarCase
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


async def get_latest_queue_entry(
    session: AsyncSession,
    *,
    application_id,
) -> AnalystQueue | None:
    q = (
        select(AnalystQueue)
        .where(AnalystQueue.application_id == application_id)
        .order_by(AnalystQueue.created_at.desc())
        .limit(1)
    )
    r = await session.execute(q)
    return r.scalar_one_or_none()


async def list_decisions(
    session: AsyncSession,
    *,
    application_id,
) -> list[Decision]:
    q = select(Decision).where(Decision.application_id == application_id).order_by(Decision.created_at.desc())
    r = await session.execute(q)
    return list(r.scalars().all())


async def list_similar_cases(
    session: AsyncSession,
    *,
    application_id,
    limit: int = 10,
) -> list[SimilarCase]:
    q = (
        select(SimilarCase)
        .where(SimilarCase.application_id == application_id)
        .order_by(SimilarCase.match_score.desc(), SimilarCase.created_at.desc())
        .limit(limit)
    )
    r = await session.execute(q)
    return list(r.scalars().all())


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

    base = select(Application).where(Application.tenant_id == tenant_id)

    score_subq = None
    if sort_by == "score":
        # There may be multiple scoring results over time; list view sorts by the
        # *latest* scoring result score (by created_at).
        latest_scoring = (
            select(
                ScoringResult.application_id.label("app_id"),
                ScoringResult.score.label("score"),
                func.row_number()
                .over(
                    partition_by=ScoringResult.application_id,
                    order_by=ScoringResult.created_at.desc(),
                )
                .label("rn"),
            )
            .subquery()
        )

        score_subq = select(latest_scoring.c.app_id, latest_scoring.c.score).where(
            latest_scoring.c.rn == 1
        ).subquery()

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
    order_col = None
    if sort_by == "created_at":
        order_col = Application.created_at
    elif sort_by == "submitted_at":
        order_col = Application.submitted_at
    elif sort_by == "amount":
        # loan_request is JSONB; cast loan_amount to numeric for sorting.
        order_col = Application.loan_request["loan_amount"].astext.cast(sa.Numeric)
    elif sort_by == "score":
        # Joined via score_subq above.
        order_col = (score_subq.c.score if score_subq is not None else None)
    else:
        order_col = Application.created_at

    if order_col is None:
        order_col = Application.created_at

    # Cursor pagination (keyset): only supported for timestamp-based sorts.
    # We keep it intentionally narrow to avoid null-handling edge cases in v1.
    cursor_value: datetime | None = None
    cursor_id: UUID | None = None

    if cursor is not None:
        if sort_by not in {"created_at", "submitted_at"}:
            raise ValueError("cursor pagination only supported for created_at/submitted_at")

        try:
            padding = "=" * (-len(cursor) % 4)
            raw = base64.urlsafe_b64decode((cursor + padding).encode("utf-8")).decode("utf-8")
            payload = json.loads(raw)
            cursor_value = datetime.fromisoformat(payload["value"])
            cursor_id = UUID(payload["id"])
        except Exception as e:  # noqa: BLE001
            raise ValueError("Invalid cursor") from e

        # If caller provided naive datetime in cursor, assume UTC.
        if cursor_value.tzinfo is None:
            cursor_value = cursor_value.replace(tzinfo=timezone.utc)

    if sort_order == "asc":
        order_expr = sa.nulls_last(order_col.asc())
        id_expr = Application.id.asc()
    else:
        order_expr = sa.nulls_last(order_col.desc())
        id_expr = Application.id.desc()

    q = base.order_by(order_expr, id_expr)

    if cursor_value is not None and cursor_id is not None:
        # Tie-break with (order_col, id) to ensure stable ordering.
        keyset = sa.tuple_(order_col, Application.id)
        if sort_order == "asc":
            q = q.where(keyset > sa.tuple_(cursor_value, cursor_id))
        else:
            q = q.where(keyset < sa.tuple_(cursor_value, cursor_id))

    if cursor is None:
        # Offset pagination (legacy)
        q = q.offset((page - 1) * page_size)

    q = q.limit(page_size)
    items = (await session.execute(q)).scalars().all()

    next_cursor: str | None = None
    if len(items) == page_size and sort_by in {"created_at", "submitted_at"}:
        last = items[-1]
        last_value = getattr(last, sort_by)
        if isinstance(last_value, datetime):
            payload = {"v": 1, "value": last_value.isoformat(), "id": str(last.id)}
            encoded = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
            next_cursor = encoded.rstrip("=")

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
