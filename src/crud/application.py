from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

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
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Application], int]:
    # Phase 2.1.2 (minimal): listing + status filter + simple pagination.
    # Tenant id is required until auth/tenant-context middleware lands.
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100

    base = select(Application).where(Application.tenant_id == tenant_id)
    if status:
        base = base.where(Application.status == status)

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

    q = base.order_by(Application.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await session.execute(q)).scalars().all()

    return items, total


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
