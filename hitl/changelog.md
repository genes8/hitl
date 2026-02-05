# Changelog

## Unreleased

- API: added POST /api/v1/applications (create application) with derived ratios + audit log entry (Phase 2 start).
- API: validate POST /api/v1/applications required fields (applicant_data/financial_data/loan_request) + tests.
- API: added GET /api/v1/applications/{id} (+ optional tenant_id scoping) + tests.
- API: added GET /api/v1/applications (list) with tenant/status/search filters + pagination + sort_by (created_at/amount) + tests.

- DB: added sync_application_status() and analytics views (v_daily_decision_summary, v_analyst_performance, v_queue_metrics).

- DB: added DB functions calculate_queue_priority() and get_active_threshold().

- DB/CI: update migration 004 down_revision to renamed 003 id.

- DB: fix SQLAlchemy reserved attribute `metadata` in ModelRegistry model (renamed to `meta`).

- DB: added model_registry, similar_cases, notifications, loan_outcomes (migration 004).
- DB/CI: fixed Alembic revision id length (kept <= 32 chars) to avoid alembic_version truncation errors.

- DB/CI: fix SQLAlchemy reserved attribute `metadata` in Application model (renamed to `meta`).

- DB/CI: fixed Alembic env import path so migrations can import `src` in CI.

- CI: fixed GitHub Actions service healthcheck options (postgres) to avoid docker invalid reference format.

- CI: added GitHub Actions workflow to run Alembic migrations + pytest on PRs and main.

- DB: added decision_thresholds + audit_logs + updated_at trigger function applied to core tables.

- DB: added core tables migration (applications, scoring_results, analyst_queues, decisions) + models scaffold.

- DB: initialized Alembic + first migration for tenants/users.

- Started Phase 1 skeleton: added docker/ + compose + minimal FastAPI app skeleton (health + ping) and first pytest.
