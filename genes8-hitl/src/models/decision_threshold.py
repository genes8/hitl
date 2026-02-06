from __future__ import annotations

import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DecisionThreshold(Base):
    __tablename__ = "decision_thresholds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    auto_approve_min: Mapped[int] = mapped_column(Integer, nullable=False)
    auto_decline_max: Mapped[int] = mapped_column(Integer, nullable=False)
    rules: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default='{}')

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    effective_from: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
