from __future__ import annotations

import logging
import os
import uuid

logger = logging.getLogger("hitl.tasks")


def emit_score_application_task(application_id: uuid.UUID) -> None:
    """Emit an async scoring task for the given application.

    This is a small compatibility wrapper:
    - In local/dev/CI where Celery isn't configured, it should be a no-op.
    - In environments that do have a broker + Celery installed, it can send a
      fire-and-forget task using `send_task`.

    Enable by setting:
      CELERY_ENABLED=1
      CELERY_BROKER_URL=...

    Optional:
      CELERY_RESULT_BACKEND=...
      CELERY_TASK_SCORE_APPLICATION_NAME=score_application
    """

    if os.getenv("CELERY_ENABLED") != "1":
        return

    broker_url = os.getenv("CELERY_BROKER_URL")
    if not broker_url:
        logger.warning("CELERY_ENABLED=1 but CELERY_BROKER_URL is not set; skipping")
        return

    task_name = os.getenv("CELERY_TASK_SCORE_APPLICATION_NAME", "score_application")
    backend = os.getenv("CELERY_RESULT_BACKEND")

    try:
        # Imported lazily to avoid introducing a hard dependency for default CI.
        from celery import Celery  # type: ignore

        celery_app = Celery("hitl", broker=broker_url, backend=backend)
        celery_app.send_task(task_name, args=[str(application_id)])
    except Exception:
        logger.exception(
            "Failed to emit Celery task %s for application_id=%s",
            task_name,
            application_id,
        )
