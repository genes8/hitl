from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ApplicationCreate(BaseModel):
    tenant_id: UUID

    external_id: str | None = None
    applicant_data: dict[str, Any]
    financial_data: dict[str, Any]
    loan_request: dict[str, Any]
    credit_bureau_data: dict[str, Any] | None = None

    source: str = "web"


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
