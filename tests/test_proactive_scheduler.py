"""Proactive analysis job: execution, per-user isolation, advisory lock."""

from types import SimpleNamespace

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


class _FakeProactive:
    def __init__(self, risks_by_user):
        self.risks_by_user = risks_by_user
        self.analyzed = []

    def analyze(self, user_id):
        self.analyzed.append(user_id)
        if user_id == 999:
            raise RuntimeError("boom")
        return {"risks": self.risks_by_user.get(user_id, [])}


class _FakeMemory:
    def __init__(self):
        self.remembered = []

    def remember(self, user_id, memory_type, content, confidence_score=1.0):
        self.remembered.append((user_id, content))


class _FakeAudit:
    AI_PROACTIVE_ANALYSIS = "AI_PROACTIVE_ANALYSIS"

    def __init__(self):
        self.records = []

    def record(self, **kwargs):
        self.records.append(kwargs)


def _install(monkeypatch, users, proactive, memory, audit, lock=None):
    lock = lock or _FakeLock(acquired=True)
    session = _FakeSession()
    monkeypatch.setattr(scheduler_module, "_open_proactive_lock", lambda: (lock, session))
    monkeypatch.setattr(scheduler_module, "SessionLocal", lambda: _FakeSession())
    monkeypatch.setattr(scheduler_module, "create_proactive_financial_service", lambda db=None: proactive)
    monkeypatch.setattr(scheduler_module, "create_financial_memory_service", lambda db=None: memory)
    monkeypatch.setattr(scheduler_module, "create_audit_service", lambda db=None: audit)

    class _FakeUserRepo:
        def __init__(self, db):
            pass

        def get_all(self):
            return [SimpleNamespace(id=u) for u in users]

    import app.repositories.user_repository as urepo
    monkeypatch.setattr(urepo, "UserRepository", _FakeUserRepo)
    return lock, session


def test_job_analyzes_all_users_and_records(monkeypatch):
    proactive = _FakeProactive({1: ["risk-a"], 2: []})
    memory = _FakeMemory()
    audit = _FakeAudit()
    _install(monkeypatch, [1, 2], proactive, memory, audit)

    scheduler_module.run_proactive_financial_analysis()

    assert proactive.analyzed == [1, 2]
    # A RISK_SIGNAL memory was stored for user 1's risk.
    assert memory.remembered == [(1, "risk-a")]
    # Both users got an AI_PROACTIVE_ANALYSIS audit row.
    assert len([r for r in audit.records if r["action"] == "AI_PROACTIVE_ANALYSIS"]) == 2


def test_one_user_failure_does_not_stop_others(monkeypatch):
    proactive = _FakeProactive({1: ["risk-a"], 3: ["risk-c"]})
    memory = _FakeMemory()
    audit = _FakeAudit()
    _install(monkeypatch, [1, 999, 3], proactive, memory, audit)

    # 999 raises inside analyze; the job must continue to user 3.
    scheduler_module.run_proactive_financial_analysis()

    assert proactive.analyzed == [1, 999, 3]
    assert (1, "risk-a") in memory.remembered
    assert (3, "risk-c") in memory.remembered


def test_lock_prevents_duplicate_execution(monkeypatch):
    proactive = _FakeProactive({})
    lock, session = _install(
        monkeypatch, [1], proactive, _FakeMemory(), _FakeAudit(),
        lock=_FakeLock(acquired=False),
    )

    scheduler_module.run_proactive_financial_analysis()

    # Nothing analyzed; lock + session cleaned up.
    assert proactive.analyzed == []
    assert lock.released is True
    assert session.closed is True


def test_proactive_job_registered_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "PROACTIVE_ANALYSIS_ENABLED", True)
    scheduler = scheduler_module.create_scheduler()
    assert scheduler.get_job("run_proactive_financial_analysis") is not None
    # Existing reminder + notification jobs remain.
    assert scheduler.get_job("send_daily_reminders") is not None


def test_proactive_job_absent_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "PROACTIVE_ANALYSIS_ENABLED", False)
    scheduler = scheduler_module.create_scheduler()
    assert scheduler.get_job("run_proactive_financial_analysis") is None
