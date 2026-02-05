"""add analyst_queues partial indexes (priority + SLA)

Revision ID: 007_queue_indexes
Revises: 006_views_and_sync_status
Create Date: 2026-02-05

"""

from alembic import op
import sqlalchemy as sa


revision = "007_queue_indexes"
down_revision = "006_views_and_sync_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_queue_priority",
        "analyst_queues",
        ["status", "priority", "created_at"],
        unique=False,
        postgresql_where=sa.text("status IN ('pending', 'assigned')"),
    )

    op.create_index(
        "idx_queue_sla",
        "analyst_queues",
        ["sla_deadline"],
        unique=False,
        postgresql_where=sa.text("status IN ('pending', 'assigned', 'in_progress')"),
    )


def downgrade() -> None:
    op.drop_index("idx_queue_sla", table_name="analyst_queues")
    op.drop_index("idx_queue_priority", table_name="analyst_queues")
