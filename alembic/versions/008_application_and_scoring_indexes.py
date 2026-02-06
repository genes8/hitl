"""add application + scoring_results indexes for listing/search performance

Revision ID: 008_application_and_scoring_indexes
Revises: 007_queue_indexes
Create Date: 2026-02-06

"""

from alembic import op
import sqlalchemy as sa

revision = "008_application_and_scoring_indexes"
down_revision = "007_queue_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Applications listing: common ordering + filters
    op.create_index(
        "idx_applications_tenant_created",
        "applications",
        ["tenant_id", sa.text("created_at DESC")],
        unique=False,
    )

    # External id search (exact / prefix): keep tenant scoped and skip NULLs
    op.create_index(
        "idx_applications_tenant_external_id",
        "applications",
        ["tenant_id", "external_id"],
        unique=False,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )

    # Sorting/scoring: selecting latest scoring_result for an application
    op.create_index(
        "idx_scoring_application_created",
        "scoring_results",
        ["application_id", sa.text("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_scoring_application_created", table_name="scoring_results")
    op.drop_index("idx_applications_tenant_external_id", table_name="applications")
    op.drop_index("idx_applications_tenant_created", table_name="applications")
