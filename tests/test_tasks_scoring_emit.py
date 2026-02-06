import sys
import types
import uuid

from src.tasks.score_application import emit_score_application_task


def test_emit_score_application_task_is_noop_when_disabled(monkeypatch):
    # Default behavior should not require Celery.
    app_id = uuid.uuid4()
    emit_score_application_task(app_id)


def test_emit_score_application_task_send_task_when_enabled(monkeypatch):
    called: dict[str, object] = {}

    class _FakeCeleryApp:
        def send_task(self, task_name: str, args: list[str]):
            called["task_name"] = task_name
            called["args"] = args

    class _FakeCelery:
        def __init__(self, *args, **kwargs):
            called["celery_init"] = {"args": args, "kwargs": kwargs}

        def send_task(self, task_name: str, args: list[str]):
            return _FakeCeleryApp().send_task(task_name, args)

    fake_celery_mod = types.ModuleType("celery")
    fake_celery_mod.Celery = _FakeCelery
    monkeypatch.setitem(sys.modules, "celery", fake_celery_mod)

    monkeypatch.setenv("CELERY_ENABLED", "1")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("CELERY_TASK_SCORE_APPLICATION_NAME", "score_application")

    app_id = uuid.uuid4()
    emit_score_application_task(app_id)

    assert called["task_name"] == "score_application"
    assert called["args"] == [str(app_id)]
