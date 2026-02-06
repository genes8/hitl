from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


def emit_score_application_task(application_id: UUID) -> None:
    """Emit an async job to score an application.

    TODO-2.1.1: Replace this placeholder with real Celery wiring once we decide
    where the worker and scheduler live (backend container vs separate worker).

    For now we keep the API-side callsite stable and non-fatal: failing to enqueue
    must not prevent creating an application.
    """

    # Placeholder implementation. This *intentionally* does not import Celery yet,
    # because the backend image currently doesn't ship Celery as a dependency.
    logger.info("score_application task emission is not wired yet (application_id=%s)", application_id)
