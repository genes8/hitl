# Changelog

## Unreleased

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
