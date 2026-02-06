from __future__ import annotations

"""Backwards-compatible wrapper for task emission.

The canonical implementation lives in :mod:`src.tasks.score_application`.
"""

from uuid import UUID

from src.tasks.score_application import emit_score_application_task as _emit


def emit_score_application_task(application_id: UUID) -> None:
    _emit(application_id)
