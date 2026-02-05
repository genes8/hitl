from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.application import Application
from src.models.audit_log import AuditLog
from src.schemas.application import ApplicationCreate, ApplicationUpdate


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

    # Optional tenant scoping (requested in hitl/todo.md / changelog).
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


async def update_application(
    session: AsyncSession,
    *,
    app: Application,
    obj_in: ApplicationUpdate,
) -> Application:
    old_value = {
        "external_id": app.external_id,
        "status": app.status,
        "applicant_data": app.applicant_data,
        "financial_data": app.financial_data,
        "loan_request": app.loan_request,
        "credit_bureau_data": app.credit_bureau_data,
        "source": app.source,
        "meta": app.meta,
    }

    if obj_in.external_id is not None:
        app.external_id = obj_in.external_id

    if obj_in.status is not None:
        app.status = obj_in.status

    if obj_in.applicant_data is not None:
        app.applicant_data = obj_in.applicant_data

    if obj_in.financial_data is not None:
        app.financial_data = obj_in.financial_data

    if obj_in.loan_request is not None:
        app.loan_request = obj_in.loan_request

    if obj_in.credit_bureau_data is not None:
        app.credit_bureau_data = obj_in.credit_bureau_data

    if obj_in.source is not None:
        app.source = obj_in.source

    # Keep derived fields in sync when the inputs change.
    if obj_in.financial_data is not None or obj_in.loan_request is not None:
        derived = _compute_derived(app.financial_data, app.loan_request)
        meta = dict(app.meta or {})
        meta["derived"] = derived
        app.meta = meta

    app.updated_at = datetime.now(timezone.utc)

    new_value = {
        "external_id": app.external_id,
        "status": app.status,
        "applicant_data": app.applicant_data,
        "financial_data": app.financial_data,
        "loan_request": app.loan_request,
        "credit_bureau_data": app.credit_bureau_data,
        "source": app.source,
        "meta": app.meta,
    }

    audit = AuditLog(
        tenant_id=app.tenant_id,
        user_id=None,
        entity_type="application",
        entity_id=app.id,
        action="update",
        old_value=old_value,
        new_value=new_value,
        change_summary="application updated",
    )
    session.add(audit)

    await session.commit()
    await session.refresh(app)
    return app
