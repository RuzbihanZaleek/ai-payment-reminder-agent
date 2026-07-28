"""Pending-action cleanup scheduler job: execution, lock, registration."""

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


class _FakeActionService:
    def __init__(self):
        self.expired_called = 0

    def expire_stale(self):
        self.expired_called += 1
        return 3


def test_cleanup_runs_when_lock_acquired(monkeypatch):
    lock, lock_session = _FakeLock(acquired=True), _FakeSession()
    monkeypatch.setattr(
        scheduler_module, "_open_pending_action_cleanup_lock", lambda: (lock, lock_session)
    )
    monkeypatch.setattr(scheduler_module, "SessionLocal", lambda: _FakeSession())
    action = _FakeActionService()
    monkeypatch.setattr(scheduler_module, "create_action_service", lambda db=None: action)

    scheduler_module.cleanup_expired_pending_actions()

    assert action.expired_called == 1
    assert lock.released is True
    assert lock_session.closed is True


def test_cleanup_skipped_when_locked(monkeypatch):
    lock, lock_session = _FakeLock(acquired=False), _FakeSession()
    monkeypatch.setattr(
        scheduler_module, "_open_pending_action_cleanup_lock", lambda: (lock, lock_session)
    )
    action = _FakeActionService()

    def _should_not_run(db=None):
        raise AssertionError("cleanup must not run when the lock is unavailable")

    monkeypatch.setattr(scheduler_module, "create_action_service", _should_not_run)

    scheduler_module.cleanup_expired_pending_actions()

    assert action.expired_called == 0
    assert lock.released is True
    assert lock_session.closed is True


def test_cleanup_job_registered_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "PENDING_ACTION_CLEANUP_ENABLED", True)
    scheduler = scheduler_module.create_scheduler()
    assert scheduler.get_job("cleanup_expired_pending_actions") is not None
    # Existing jobs remain untouched.
    assert scheduler.get_job("send_daily_reminders") is not None


def test_cleanup_job_absent_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "PENDING_ACTION_CLEANUP_ENABLED", False)
    scheduler = scheduler_module.create_scheduler()
    assert scheduler.get_job("cleanup_expired_pending_actions") is None
