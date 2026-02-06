"""create core application/scoring/queue/decision tables

Revision ID: 002_create_core_tables
Revises: 001_create_tenants_users
Create Date: 2026-02-04

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "002_create_core_tables"
down_revision = "001_create_tenants_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("applicant_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("financial_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("loan_request", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("credit_bureau_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source", sa.String(length=50), server_default=sa.text("'web'"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_applications_tenant_status", "applications", ["tenant_id", "status"], unique=False)
    op.create_index("idx_applications_submitted", "applications", ["tenant_id", sa.text("submitted_at DESC")], unique=False)

    op.create_table(
        "scoring_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_id", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("probability_default", sa.Numeric(5, 4), nullable=False),
        sa.Column("risk_category", sa.String(length=20), nullable=False),
        sa.Column("routing_decision", sa.String(length=20), nullable=False),
        sa.Column("threshold_config_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("shap_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("top_factors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scoring_time_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_scoring_application", "scoring_results", ["application_id"], unique=False)
    op.create_index("idx_scoring_routing", "scoring_results", ["routing_decision"], unique=False)

    op.create_table(
        "analyst_queues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("analyst_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("priority", sa.Integer(), server_default=sa.text("50"), nullable=False),
        sa.Column("priority_reason", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sla_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sla_breached", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("routing_reason", sa.String(length=100), nullable=True),
        sa.Column("score_at_routing", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    op.create_table(
        "decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scoring_result_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scoring_results.id"), nullable=True),
        sa.Column("analyst_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decision_type", sa.String(length=30), nullable=False),
        sa.Column("decision_outcome", sa.String(length=20), nullable=False),
        sa.Column("approved_terms", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("reasoning_category", sa.String(length=50), nullable=True),
        sa.Column("override_flag", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("override_direction", sa.String(length=20), nullable=True),
        sa.Column("override_justification", sa.Text(), nullable=True),
        sa.Column("override_approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("override_approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_time_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_decisions_application", "decisions", ["application_id"], unique=False)
    op.create_index("idx_decisions_override", "decisions", ["override_flag"], unique=False, postgresql_where=sa.text("override_flag = true"))


def downgrade() -> None:
    op.drop_index("idx_decisions_override", table_name="decisions")
    op.drop_index("idx_decisions_application", table_name="decisions")
    op.drop_table("decisions")

    op.drop_table("analyst_queues")

    op.drop_index("idx_scoring_routing", table_name="scoring_results")
    op.drop_index("idx_scoring_application", table_name="scoring_results")
    op.drop_table("scoring_results")

    op.drop_index("idx_applications_submitted", table_name="applications")
    op.drop_index("idx_applications_tenant_status", table_name="applications")
    op.drop_table("applications")
