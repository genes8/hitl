"""add indexes to speed up applications listing filters/sorts

Revision ID: 008_app_listing_indexes
Revises: 007_queue_indexes
Create Date: 2026-02-06

"""

from alembic import op
import sqlalchemy as sa

revision = "008_app_listing_indexes"
down_revision = "007_queue_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Supports GET /applications common access patterns:
    # - tenant-scoped ordering/filtering by created_at
    # - searching by external_id
    # - sorting by loan amount (jsonb -> numeric)

    op.create_index(
        "idx_applications_tenant_created",
        "applications",
        ["tenant_id", sa.text("created_at DESC")],
        unique=False,
    )

    op.create_index(
        "idx_applications_tenant_external_id",
        "applications",
        ["tenant_id", "external_id"],
        unique=False,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )

    op.create_index(
        "idx_applications_tenant_loan_amount",
        "applications",
        ["tenant_id", sa.text("((loan_request->>'loan_amount')::numeric)")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_applications_tenant_loan_amount", table_name="applications")
    op.drop_index("idx_applications_tenant_external_id", table_name="applications")
    op.drop_index("idx_applications_tenant_created", table_name="applications")
