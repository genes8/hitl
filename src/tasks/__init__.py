"""Background task entrypoints.

We intentionally keep this lightweight so that the HTTP API can *emit* jobs without
hard-requiring Celery (or any specific broker) during early iterations.

When Celery wiring lands, this package is the intended home for the Celery app and
@task definitions.
"""
