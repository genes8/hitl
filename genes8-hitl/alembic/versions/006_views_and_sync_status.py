"""add sync_application_status function and analytics views

Revision ID: 006_views_and_sync_status
Revises: 005_db_functions
Create Date: 2026-02-05

"""

from alembic import op

revision = "006_views_and_sync_status"
down_revision = "005_db_functions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Sync application status from decisions/queue.
    # Conservative logic: if latest decision exists -> approved/declined; else if in queue -> review; else keep current.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION sync_application_status(p_application_id UUID)
        RETURNS VOID AS $$
        DECLARE
          v_decision_outcome TEXT;
          v_in_queue BOOLEAN;
        BEGIN
          SELECT d.decision_outcome
          INTO v_decision_outcome
          FROM decisions d
          WHERE d.application_id = p_application_id
          ORDER BY d.created_at DESC
          LIMIT 1;

          IF v_decision_outcome IS NOT NULL THEN
            IF v_decision_outcome = 'approved' THEN
              UPDATE applications SET status='approved' WHERE id=p_application_id;
              RETURN;
            ELSIF v_decision_outcome = 'declined' THEN
              UPDATE applications SET status='declined' WHERE id=p_application_id;
              RETURN;
            END IF;
          END IF;

          SELECT EXISTS(
            SELECT 1
            FROM analyst_queues q
            WHERE q.application_id = p_application_id
              AND q.status IN ('pending','assigned','in_progress')
          )
          INTO v_in_queue;

          IF v_in_queue THEN
            UPDATE applications SET status='review' WHERE id=p_application_id;
          END IF;
        END;
        $$ language 'plpgsql';
        """
    )

    # Views
    op.execute(
        """
        CREATE OR REPLACE VIEW v_daily_decision_summary AS
        SELECT
          date_trunc('day', d.created_at) AS day,
          COUNT(*) AS total_decisions,
          SUM(CASE WHEN d.decision_type LIKE 'auto_%' THEN 1 ELSE 0 END) AS auto_decisions,
          SUM(CASE WHEN d.decision_outcome='approved' THEN 1 ELSE 0 END) AS approvals,
          SUM(CASE WHEN d.decision_outcome='declined' THEN 1 ELSE 0 END) AS declines,
          AVG(d.review_time_seconds) AS avg_review_time_seconds
        FROM decisions d
        GROUP BY 1
        ORDER BY 1 DESC;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW v_analyst_performance AS
        SELECT
          d.analyst_id,
          COUNT(*) AS total_decisions,
          AVG(d.review_time_seconds) AS avg_review_time_seconds,
          SUM(CASE WHEN d.override_flag THEN 1 ELSE 0 END) AS overrides,
          SUM(CASE WHEN d.decision_outcome='approved' THEN 1 ELSE 0 END) AS approvals,
          SUM(CASE WHEN d.decision_outcome='declined' THEN 1 ELSE 0 END) AS declines
        FROM decisions d
        WHERE d.analyst_id IS NOT NULL
        GROUP BY d.analyst_id
        ORDER BY total_decisions DESC;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW v_queue_metrics AS
        SELECT
          q.status,
          COUNT(*) AS count,
          AVG(EXTRACT(EPOCH FROM (NOW() - q.created_at))) AS avg_age_seconds,
          SUM(CASE WHEN q.sla_breached THEN 1 ELSE 0 END) AS breached
        FROM analyst_queues q
        GROUP BY q.status
        ORDER BY q.status;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_queue_metrics;")
    op.execute("DROP VIEW IF EXISTS v_analyst_performance;")
    op.execute("DROP VIEW IF EXISTS v_daily_decision_summary;")

    op.execute("DROP FUNCTION IF EXISTS sync_application_status(UUID);")
