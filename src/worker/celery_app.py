from __future__ import annotations

from celery import Celery

from src.config import settings


celery_app = Celery(
    "hitl",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
