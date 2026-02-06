"""Async/background task entrypoints.

Keep this package lightweight so the API can emit jobs without hard-requiring
Celery (or any broker) in default dev/CI.

When Celery wiring lands, this package is the intended home for the Celery app and
@task definitions.
"""
