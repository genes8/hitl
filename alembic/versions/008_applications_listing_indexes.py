"""add indexes to speed up application listing/filtering

Revision ID: 008_applications_listing_indexes
Revises: 007_queue_indexes
Create Date: 2026-02-06

"""

from alembic import op
import sqlalchemy as sa


revision = "008_applications_listing_indexes"
down_revision = "007_queue_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Listing endpoint always scopes by tenant_id and commonly sorts/filters on created_at.
    # This composite index supports:
    # - WHERE tenant_id = ?
    # - ORDER BY created_at DESC/ASC (with tie-breaker id)
    # - created_at range scans for from_date/to_date filters
    op.create_index(
        "idx_applications_tenant_created_at",
        "applications",
        ["tenant_id", sa.text("created_at DESC")],
        unique=False,
    )

    # Search supports external_id ILIKE; a btree index helps for exact/prefix matches.
    # (For full substring search we'd want pg_trgm, but we keep v0 dependency-free.)
    op.create_index(
        "idx_applications_tenant_external_id",
        "applications",
        ["tenant_id", "external_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_applications_tenant_external_id", table_name="applications")
    op.drop_index("idx_applications_tenant_created_at", table_name="applications")
