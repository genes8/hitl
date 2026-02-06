from __future__ import annotations

import uuid

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class LoanOutcome(Base):
    __tablename__ = "loan_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)

    outcome: Mapped[str] = mapped_column(String(30), nullable=False)  # e.g. defaulted, repaid, active
    defaulted: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False, server_default="false")

    months_on_book: Mapped[int | None] = mapped_column(sa.Integer(), nullable=True)
    loss_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    extra: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default='{}')

    observed_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
