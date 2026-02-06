# Changelog

## Unreleased

- DB: add indexes to speed up GET /api/v1/applications listing (tenant+created_at, tenant+external_id, tenant+loan_amount).
- API: enqueue scoring task on application intake (dispatcher shim; Celery wiring in TODO-2.4.1).
- Dev: add idempotent dev seed script (tenant/users/default threshold) for local/dev environments.
- API: add search + sorting (created_at/amount, asc/desc) to GET /api/v1/applications (+ tests).
- API: validate from_date <= to_date and validate sort_by/sort_order (422).
- API: add sort_by=score option to GET /api/v1/applications (NULL scores last) (+ tests).
- API: add from_date/to_date filters to GET /api/v1/applications (+ tests).
- API: add cursor pagination option (sort_by=created_at) to GET /api/v1/applications (+ tests).
- Tests: add query-plan perf guard for GET /api/v1/applications (asserts tenant+created_at index is used for large tenant dataset).
- API: add GET /api/v1/applications listing endpoint with tenant_id scoping, status filter, and simple pagination (+ tests).
- API: add request ID middleware (X-Request-ID passthrough / generation) + lightweight access logging for easier tracing.
- DB: add tests for Postgres functions (calculate_queue_priority / get_active_threshold / sync_application_status) and for key schema constraints.

- DB/CI: added pytest smoke-test to verify Alembic migrations are reversible (upgrade -> downgrade -> upgrade).
- Docker: backend image now installs psycopg[binary] so Alembic can run against Postgres in-container.

- API: add GET /api/v1/applications/{id} (basic detail endpoint) + tests.

- API: added POST /api/v1/applications (create application) with derived ratios + audit log entry (Phase 2 start).
- API: added GET /api/v1/applications/{id} (detail) with optional tenant scoping via `tenant_id` query param; includes latest scoring_result when present.
- API: validate POST /api/v1/applications required fields (applicant_data/financial_data/loan_request) + tests.

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
