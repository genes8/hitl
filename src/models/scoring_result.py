from __future__ import annotations

import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ScoringResult(Base):
    __tablename__ = "scoring_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)

    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    score: Mapped[int] = mapped_column(Integer, nullable=False)
    probability_default: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    risk_category: Mapped[str] = mapped_column(String(20), nullable=False)
    routing_decision: Mapped[str] = mapped_column(String(20), nullable=False)

    threshold_config_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    features: Mapped[dict] = mapped_column(JSONB, nullable=False)
    shap_values: Mapped[dict] = mapped_column(JSONB, nullable=False)
    top_factors: Mapped[dict] = mapped_column(JSONB, nullable=False)

    scoring_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
