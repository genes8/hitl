from __future__ import annotations

import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    scoring_result_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("scoring_results.id"), nullable=True)
    analyst_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    decision_type: Mapped[str] = mapped_column(String(30), nullable=False)
    decision_outcome: Mapped[str] = mapped_column(String(20), nullable=False)

    approved_terms: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    conditions: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    reasoning_category: Mapped[str | None] = mapped_column(String(50), nullable=True)

    override_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    override_direction: Mapped[str | None] = mapped_column(String(20), nullable=True)
    override_justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    override_approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    override_approved_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    review_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
