from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


def emit_score_application_task(application_id: UUID) -> None:
    """Emit an async job to score an application.

    TODO-2.1.1: Celery wiring.

    This function must be non-fatal: failing to enqueue must not prevent creating
    an application.
    """

    try:
        # Import lazily so the HTTP app can start even if Celery isn't installed
        # in a given environment.
        from src.worker import score_application

        score_application.delay(str(application_id))
    except Exception:
        logger.exception(
            "Failed to emit score_application task (application_id=%s)",
            application_id,
        )
