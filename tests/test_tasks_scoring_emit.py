import sys
import types
import uuid

from src.tasks.scoring import emit_score_application_task


def test_emit_score_application_task_calls_celery_delay(monkeypatch):
    called: dict[str, str] = {}

    class _FakeTask:
        @staticmethod
        def delay(application_id: str) -> None:
            called["application_id"] = application_id

    fake_worker = types.ModuleType("src.worker")
    fake_worker.score_application = _FakeTask

    # Avoid importing real Celery in unit tests; we only care that we call .delay.
    monkeypatch.setitem(sys.modules, "src.worker", fake_worker)

    app_id = uuid.uuid4()
    emit_score_application_task(app_id)

    assert called["application_id"] == str(app_id)
