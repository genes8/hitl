from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.application import Application
from src.models.scoring_result import ScoringResult
from src.models.audit_log import AuditLog
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
    stmt = select(Application).where(Application.id == application_id)
    if tenant_id is not None:
        stmt = stmt.where(Application.tenant_id == tenant_id)

    res = await session.execute(stmt)
    return res.scalar_one_or_none()


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


async def list_applications(
    session: AsyncSession,
    *,
    tenant_id=None,
    status: str | None = None,
    search: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
    cursor: str | None = None,
) -> tuple[list[Application], int, str | None, bool | None]:
    """Return (items, total, next_cursor, has_more).

    By default pagination is page-based. If `cursor` is provided, cursor-based
    pagination is used (currently only supported for sort_by=created_at).
    """

    if page < 1:
        raise ValueError("page must be >= 1")
    if page_size < 1 or page_size > 100:
        raise ValueError("page_size must be between 1 and 100")

    use_cursor = cursor is not None

    # Base filters
    stmt = select(Application)

    if tenant_id is not None:
        stmt = stmt.where(Application.tenant_id == tenant_id)

    if status is not None:
        stmt = stmt.where(Application.status == status)

    if from_date is not None:
        stmt = stmt.where(Application.created_at >= from_date)

    if to_date is not None:
        stmt = stmt.where(Application.created_at <= to_date)

    if search:
        # Spec: external_id, applicant name.
        # Note: applicant_data is JSONB. We search case-insensitive.
        like = f"%{search}%"
        stmt = stmt.where(
            (
                Application.external_id.ilike(like)
                | Application.applicant_data["name"].as_string().ilike(like)
            )
        )

    needs_score_join = sort_by == "score"

    if needs_score_join:
        stmt = stmt.outerjoin(ScoringResult, ScoringResult.application_id == Application.id)

    if use_cursor and sort_by != "created_at":
        raise ValueError("cursor pagination is only supported for sort_by=created_at")

    # Sorting
    if sort_by == "created_at":
        sort_col = Application.created_at
    elif sort_by == "amount":
        sort_col = Application.loan_request["loan_amount"].as_float()
    elif sort_by == "score":
        sort_col = ScoringResult.score
    else:
        raise ValueError("sort_by must be one of: created_at, amount, score")

    if sort_order not in ("asc", "desc"):
        raise ValueError("sort_order must be one of: asc, desc")

    # Deterministic ordering for created_at sorting (needed for cursor pagination).
    if sort_by == "created_at":
        if sort_order == "asc":
            stmt = stmt.order_by(sort_col.asc(), Application.id.asc())
        else:
            stmt = stmt.order_by(sort_col.desc(), Application.id.desc())
    else:
        if sort_order == "asc":
            stmt = stmt.order_by(sort_col.asc().nullslast())
        else:
            stmt = stmt.order_by(sort_col.desc().nullslast())

    # Total count
    subq = stmt.subquery()
    if needs_score_join:
        count_stmt = select(func.count(func.distinct(subq.c.id)))
    else:
        count_stmt = select(func.count())

    count_stmt = count_stmt.select_from(subq)
    total = int((await session.execute(count_stmt)).scalar_one())

    next_cursor: str | None = None
    has_more: bool | None = None

    if use_cursor:
        # Cursor format: "<created_at_iso>|<uuid>".
        try:
            raw_ts, raw_id = cursor.split("|", 1)
            # Allow Z suffix.
            dt = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            cur_id = UUID(raw_id)
        except Exception as e:  # pragma: no cover
            raise ValueError("cursor must be in format '<created_at_iso>|<uuid>'") from e

        if sort_order == "asc":
            stmt = stmt.where(
                (Application.created_at > dt)
                | ((Application.created_at == dt) & (Application.id > cur_id))
            )
        else:
            stmt = stmt.where(
                (Application.created_at < dt)
                | ((Application.created_at == dt) & (Application.id < cur_id))
            )

        # Fetch one extra row so we can report `has_more`.
        stmt = stmt.limit(page_size + 1)
        res = await session.execute(stmt)
        all_items = list(res.scalars().unique().all())
        has_more = len(all_items) > page_size
        items = all_items[:page_size]

        if has_more and items:
            last = items[-1]
            next_cursor = f"{last.created_at.isoformat()}|{last.id}"

        return items, total, next_cursor, has_more

    # Page-based pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    res = await session.execute(stmt)
    items = list(res.scalars().unique().all())
    return items, total, None, None
