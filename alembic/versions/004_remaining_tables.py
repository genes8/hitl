"""add model registry, similar cases, notifications, loan outcomes

Revision ID: 004_remaining_tables
Revises: 003_thresh_audit_trig
Create Date: 2026-02-05

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "004_remaining_tables"
down_revision = "003_thresh_audit_trig"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_registry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("model_id", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("stage", sa.String(length=30), server_default=sa.text("'production'"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("artifact_uri", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    op.create_table(
        "similar_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("matched_application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("match_score", sa.Float(), nullable=False),
        sa.Column("features_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("outcome_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("method", sa.String(length=50), server_default=sa.text("'vector'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_similar_cases_application", "similar_cases", ["application_id"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("delivered_channels", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_notifications_tenant_created", "notifications", ["tenant_id", sa.text("created_at DESC")], unique=False)

    op.create_table(
        "loan_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("outcome", sa.String(length=30), nullable=False),
        sa.Column("defaulted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("months_on_book", sa.Integer(), nullable=True),
        sa.Column("loss_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_loan_outcomes_application", "loan_outcomes", ["application_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_loan_outcomes_application", table_name="loan_outcomes")
    op.drop_table("loan_outcomes")

    op.drop_index("idx_notifications_tenant_created", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("idx_similar_cases_application", table_name="similar_cases")
    op.drop_table("similar_cases")

    op.drop_table("model_registry")
