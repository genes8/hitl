from __future__ import annotations

from src.worker.celery_app import celery_app


@celery_app.task(name="score_application")
def score_application(application_id: str) -> None:
    """Score an application asynchronously.

    This is a Phase 2 placeholder task. The actual scoring implementation will
    land in Sprint 2.4 (Scoring Worker Task) once the ML service is available.
    """

    # Intentionally no-op for now.
    return None
