from __future__ import annotations

from uuid import UUID


def enqueue_score_application(*, application_id: UUID) -> None:
    """Enqueue asynchronous scoring for an application.

    Phase 2.1.1 requires that we trigger scoring automatically on intake.

    We intentionally keep this as a lightweight shim:
    - In environments where Celery is not configured yet, this is a safe no-op.
    - Once Celery wiring lands (TODO-2.4.1), this function should call the
      Celery task (e.g. score_application.delay(str(application_id))).
    """

    # Celery is introduced later (TODO-2.4.1). Avoid importing it here so the
    # API can run/tests can import without Celery installed.
    return None
