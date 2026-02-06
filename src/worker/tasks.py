from __future__ import annotations

import logging

from src.worker.celery_app import celery_app


logger = logging.getLogger(__name__)


@celery_app.task(name="hitl.score_application")
def score_application(application_id: str) -> None:
    """Placeholder scoring task.

    TODO-2.4.2 will implement the real scoring workflow.
    """

    logger.info("score_application task enqueued", extra={"application_id": application_id})
