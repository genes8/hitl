from __future__ import annotations

import logging

from celery import Celery

from src.config import settings

logger = logging.getLogger(__name__)


# Celery entrypoint.
#
# We keep this module importable both by the API (for task emission) and by the
# worker/scheduler containers (celery -A src.worker worker/beat).
celery_app = Celery(
    "hitl",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    timezone="UTC",
)


@celery_app.task(name="score_application")
def score_application(application_id: str) -> None:
    """Score an application asynchronously.

    TODO-2.1.1 (follow-ups):
    - Pull application payload from DB
    - Call ML service (settings.ML_SERVICE_URL once that setting exists)
    - Persist ScoringResult row (+ audit log)

    For now, this is a stub so that the queue wiring is real end-to-end.
    """

    logger.info("score_application received (application_id=%s)", application_id)
