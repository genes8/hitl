"""add db functions calculate_queue_priority and get_active_threshold

Revision ID: 005_db_functions
Revises: 004_remaining_tables
Create Date: 2026-02-05

"""

from alembic import op

revision = "005_db_functions"
down_revision = "004_remaining_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION calculate_queue_priority(
          p_score INTEGER,
          p_loan_amount DECIMAL,
          p_is_vip BOOLEAN DEFAULT FALSE,
          p_sla_hours_remaining DECIMAL DEFAULT 24
        ) RETURNS INTEGER AS $$
        DECLARE
          v_priority INTEGER := 50;
        BEGIN
          IF p_is_vip THEN
            RETURN 10;
          END IF;

          IF p_loan_amount > 5000000 THEN
            v_priority := v_priority - 15;
          ELSIF p_loan_amount > 2000000 THEN
            v_priority := v_priority - 10;
          ELSIF p_loan_amount > 1000000 THEN
            v_priority := v_priority - 5;
          END IF;

          IF p_sla_hours_remaining < 2 THEN
            v_priority := v_priority - 20;
          ELSIF p_sla_hours_remaining < 4 THEN
            v_priority := v_priority - 10;
          ELSIF p_sla_hours_remaining < 8 THEN
            v_priority := v_priority - 5;
          END IF;

          RETURN GREATEST(1, LEAST(100, v_priority));
        END;
        $$ language 'plpgsql';
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION get_active_threshold(p_tenant_id UUID)
        RETURNS TABLE (threshold_id UUID, auto_approve_min INTEGER, auto_decline_max INTEGER, rules JSONB)
        AS $$
        BEGIN
          RETURN QUERY
          SELECT dt.id, dt.auto_approve_min, dt.auto_decline_max, dt.rules
          FROM decision_thresholds dt
          WHERE dt.tenant_id = p_tenant_id
            AND dt.is_active = true
            AND dt.effective_from <= NOW()
            AND (dt.effective_to IS NULL OR dt.effective_to > NOW())
          ORDER BY dt.effective_from DESC
          LIMIT 1;
        END;
        $$ language 'plpgsql';
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS get_active_threshold(UUID);")
    op.execute("DROP FUNCTION IF EXISTS calculate_queue_priority(INTEGER, DECIMAL, BOOLEAN, DECIMAL);")
