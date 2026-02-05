from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


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
        # Keep the payload flexible (dict blobs) but enforce a minimal contract
        # for Phase 2.1.1 intake.
        applicant_name = (self.applicant_data or {}).get("name")
        if not applicant_name:
            raise ValueError("applicant_data.name is required")

        fin = self.financial_data or {}
        for k in ("net_monthly_income", "monthly_obligations", "existing_loans_payment"):
            if fin.get(k) is None:
                raise ValueError(f"financial_data.{k} is required")

        loan = self.loan_request or {}
        for k in ("loan_amount", "estimated_payment"):
            if loan.get(k) is None:
                raise ValueError(f"loan_request.{k} is required")

        # Basic numeric sanity checks; detailed rules will evolve.
        if float(fin.get("net_monthly_income", 0) or 0) <= 0:
            raise ValueError("financial_data.net_monthly_income must be > 0")
        if float(loan.get("loan_amount", 0) or 0) <= 0:
            raise ValueError("loan_request.loan_amount must be > 0")
        if float(loan.get("estimated_payment", 0) or 0) <= 0:
            raise ValueError("loan_request.estimated_payment must be > 0")

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

    submitted_at: datetime
    expires_at: datetime | None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
