"""add decision thresholds, audit logs, and updated_at triggers

Revision ID: 003_thresh_audit_trig
Revises: 002_create_core_tables
Create Date: 2026-02-04

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "003_thresh_audit_trig"
down_revision = "002_create_core_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # decision_thresholds
    op.create_table(
        "decision_thresholds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("auto_approve_min", sa.Integer(), nullable=False),
        sa.Column("auto_decline_max", sa.Integer(), nullable=False),
        sa.Column("rules", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("auto_decline_max < auto_approve_min", name="chk_threshold_range"),
    )

    # audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("old_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("new_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_audit_entity", "audit_logs", ["entity_type", "entity_id"], unique=False)
    op.create_index("idx_audit_created", "audit_logs", ["tenant_id", sa.text("created_at DESC")], unique=False)

    # triggers
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
          NEW.updated_at = NOW();
          RETURN NEW;
        END;
        $$ language 'plpgsql';
        """
    )

    # apply to tables that have updated_at
    for table in [
        "tenants",
        "users",
        "applications",
        "analyst_queues",
        "decision_thresholds",
    ]:
        op.execute(
            f"""
            DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table};
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
            """
        )


def downgrade() -> None:
    for table in [
        "decision_thresholds",
        "analyst_queues",
        "applications",
        "users",
        "tenants",
    ]:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table};")

    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")

    op.drop_index("idx_audit_created", table_name="audit_logs")
    op.drop_index("idx_audit_entity", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_table("decision_thresholds")
