"""Scheduler integration for the notification worker job."""

import app.scheduler as scheduler_module
from app.core.config import settings


class _FakeLock:
    def __init__(self, acquired=True):
        self._acquired = acquired
        self.released = False

    def acquire(self):
        return self._acquired

    def release(self):
        self.released = True


class _FakeSession:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_worker_job_registered_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "NOTIFICATION_WORKER_ENABLED", True)

    scheduler = scheduler_module.create_scheduler()

    assert scheduler.get_job("process_notification_outbox") is not None
    # The reminder job is always registered and independent.
    assert scheduler.get_job("send_daily_reminders") is not None


def test_worker_job_absent_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "NOTIFICATION_WORKER_ENABLED", False)

    scheduler = scheduler_module.create_scheduler()

    assert scheduler.get_job("process_notification_outbox") is None
    # Disabling the worker never affects the reminder job.
    assert scheduler.get_job("send_daily_reminders") is not None


def test_lock_prevents_duplicate_worker_execution(monkeypatch):
    lock = _FakeLock(acquired=False)
    session = _FakeSession()
    monkeypatch.setattr(
        scheduler_module, "_open_notification_worker_lock", lambda: (lock, session)
    )

    built = {"called": False}

    def _spy(db=None):
        built["called"] = True
        raise AssertionError("worker must not run when lock unavailable")

    monkeypatch.setattr(scheduler_module, "create_notification_worker", _spy)

    scheduler_module.process_notification_outbox()

    assert built["called"] is False
    assert lock.released is True
    assert session.closed is True


def test_worker_runs_when_lock_acquired(monkeypatch):
    lock = _FakeLock(acquired=True)
    lock_session = _FakeSession()
    monkeypatch.setattr(
        scheduler_module, "_open_notification_worker_lock", lambda: (lock, lock_session)
    )
    # Avoid opening a real DB session for the worker.
    monkeypatch.setattr(scheduler_module, "SessionLocal", lambda: _FakeSession())

    ran = {"called": False}

    class _SpyWorker:
        def process_batch(self):
            ran["called"] = True

    monkeypatch.setattr(
        scheduler_module, "create_notification_worker", lambda db=None: _SpyWorker()
    )

    scheduler_module.process_notification_outbox()

    assert ran["called"] is True
    assert lock.released is True
    assert lock_session.closed is True
