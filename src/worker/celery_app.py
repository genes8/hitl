from __future__ import annotations

from celery import Celery

from src.config import settings


def make_celery() -> Celery:
    """Create the Celery app.

    Note: we keep this in a function so tests can import tasks without eagerly
    touching global state beyond settings.
    """

    celery = Celery(
        "hitl",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["src.worker.tasks"],
    )

    # Keep defaults minimal; Phase 2.4 will add more complete Celery configuration.
    celery.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
    )

    return celery


celery_app = make_celery()
