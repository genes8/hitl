"""Background task dispatchers.

We keep task enqueue logic behind small functions so API code can call into it
without depending directly on Celery (which is wired in Phase 2.4).
"""
