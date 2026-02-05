from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SimilarCase(Base):
    __tablename__ = "similar_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)

    matched_application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    match_score: Mapped[float] = mapped_column(sa.Float(), nullable=False)

    features_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    outcome_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)

    method: Mapped[str] = mapped_column(String(50), nullable=False, server_default="vector")

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
