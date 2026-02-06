"""add index to speed up tenant+status application listing

Revision ID: 009_applications_status_idx
Revises: 008_applications_listing_indexes
Create Date: 2026-02-06

"""

from alembic import op
import sqlalchemy as sa


revision = "009_applications_status_idx"
down_revision = "008_applications_listing_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # GET /applications commonly uses status filter together with tenant scope and created_at ordering.
    # This index helps:
    # - WHERE tenant_id = ? AND status = ?
    # - ORDER BY created_at DESC/ASC
    op.create_index(
        "idx_applications_tenant_status_created_at",
        "applications",
        ["tenant_id", "status", sa.text("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_applications_tenant_status_created_at",
        table_name="applications",
    )
