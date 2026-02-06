from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from src.schemas.analyst_queue import QueueInfoRead
from src.schemas.decision import DecisionRead
from src.schemas.scoring_result import ScoringResultRead


class ApplicationCreate(BaseModel):
    tenant_id: UUID

    external_id: str | None = None
    applicant_data: dict[str, Any]
    financial_data: dict[str, Any]
    loan_request: dict[str, Any]
    credit_bureau_data: dict[str, Any] | None = None

    source: str = "web"

    @model_validator(mode="after")
    def _validate_required_fields(self) -> "ApplicationCreate":
        # TODO-2.1.1 validations: enforce minimal required fields for intake.
        missing: list[str] = []

        def require(container: dict[str, Any] | None, key: str, *, path: str) -> Any:
            if not isinstance(container, dict):
                missing.append(f"{path} (must be an object)")
                return None
            if key not in container or container.get(key) in (None, ""):
                missing.append(f"{path}.{key}")
                return None
            return container.get(key)

        require(self.applicant_data, "name", path="applicant_data")

        net_income = require(self.financial_data, "net_monthly_income", path="financial_data")
        require(self.financial_data, "monthly_obligations", path="financial_data")
        require(self.financial_data, "existing_loans_payment", path="financial_data")

        loan_amount = require(self.loan_request, "loan_amount", path="loan_request")
        est_payment = require(self.loan_request, "estimated_payment", path="loan_request")

        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        # Basic sanity checks: enforce positive numeric values where appropriate.
        def must_be_positive_number(value: Any, *, field: str) -> None:
            try:
                num = float(value)
            except (TypeError, ValueError) as e:
                raise ValueError(f"{field} must be a number") from e
            if num <= 0:
                raise ValueError(f"{field} must be > 0")

        must_be_positive_number(net_income, field="financial_data.net_monthly_income")
        must_be_positive_number(loan_amount, field="loan_request.loan_amount")
        must_be_positive_number(est_payment, field="loan_request.estimated_payment")

        return self


class ApplicationListItem(BaseModel):
    id: UUID
    tenant_id: UUID

    external_id: str | None
    status: str

    submitted_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApplicationListResponse(BaseModel):
    items: list[ApplicationListItem]
    total: int
    page: int
    page_size: int
    next_cursor: str | None = None


class ApplicationRead(BaseModel):
    id: UUID
    tenant_id: UUID

    external_id: str | None
    status: str

    applicant_data: dict[str, Any]
    financial_data: dict[str, Any]
    loan_request: dict[str, Any]
    credit_bureau_data: dict[str, Any] | None

    source: str
    meta: dict[str, Any] = Field(default_factory=dict)

    # TODO-2.1.3: extend with related resources as we build them out.
    scoring_result: ScoringResultRead | None = None
    queue_info: QueueInfoRead | None = None
    decision_history: list[DecisionRead] = Field(default_factory=list)

    submitted_at: datetime
    expires_at: datetime | None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
