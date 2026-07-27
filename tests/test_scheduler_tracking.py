import pytest

import app.scheduler as scheduler_module
from app.enums.scheduler_run_status import SchedulerRunStatus


class FakeContract:

    def __init__(self, contract_id):
        self.id = contract_id


class FakeReminderService:

    def __init__(self, contracts):
        self.contracts = contracts

    def get_pending_reminders(self):

        return self.contracts


class FakeReminderExecutionService:

    def __init__(self, fail_ids=()):
        self.fail_ids = set(fail_ids)
        self.executed = []

    def execute(self, contract):

        self.executed.append(contract.id)

        if contract.id in self.fail_ids:
            raise RuntimeError("reminder failed")


class FakeSchedulerRun:

    def __init__(self):
        self.id = 99
        self.status = None
        self.total_contracts = 0
        self.successful_count = 0
        self.failed_count = 0
        self.completed_at = None


class FakeSchedulerRunRepository:

    def __init__(self):
        self.run = FakeSchedulerRun()
        self.created = None
        self.status_updates = []

    def create(self, scheduler_run):

        self.created = scheduler_run

        return self.run

    def update_status(self, scheduler_run, status):

        scheduler_run.status = status
        self.status_updates.append(status)

        return scheduler_run


class FakeSchedulerEventRepository:

    def __init__(self):
        self.events = []

    def create(self, scheduler_event):

        self.events.append(scheduler_event)

        return scheduler_event


class _FakeLock:
    def acquire(self):
        return True

    def release(self):
        pass


class _FakeLockSession:
    def close(self):
        pass


def _stub_lock(monkeypatch):
    # The advisory lock always succeeds in these unit tests (no Postgres).
    monkeypatch.setattr(
        scheduler_module,
        "_open_scheduler_lock",
        lambda: (_FakeLock(), _FakeLockSession()),
    )


def _install(monkeypatch, contracts, execution_service, run_repo, event_repo):

    _stub_lock(monkeypatch)

    monkeypatch.setattr(
        scheduler_module,
        "create_reminder_service",
        lambda: FakeReminderService(contracts),
    )
    monkeypatch.setattr(
        scheduler_module,
        "create_reminder_execution_service",
        lambda: execution_service,
    )
    monkeypatch.setattr(
        scheduler_module,
        "create_scheduler_run_repository",
        lambda: run_repo,
    )
    monkeypatch.setattr(
        scheduler_module,
        "create_scheduler_event_repository",
        lambda: event_repo,
    )


def test_successful_scheduler_execution(monkeypatch):

    contracts = [FakeContract(1), FakeContract(2)]
    execution_service = FakeReminderExecutionService()
    run_repo = FakeSchedulerRunRepository()
    event_repo = FakeSchedulerEventRepository()

    _install(monkeypatch, contracts, execution_service, run_repo, event_repo)

    scheduler_module.send_daily_reminders()

    # Run created RUNNING, then completed
    assert run_repo.created.run_type == "daily_reminders"
    assert run_repo.created.status == SchedulerRunStatus.RUNNING
    assert run_repo.run.status == SchedulerRunStatus.COMPLETED
    assert run_repo.run.completed_at is not None

    # One SENT event per contract
    assert [e.status for e in event_repo.events] == ["SENT", "SENT"]
    assert [e.contract_id for e in event_repo.events] == [1, 2]
    assert all(e.scheduler_run_id == 99 for e in event_repo.events)


def test_failed_contract_does_not_stop_others(monkeypatch):

    contracts = [FakeContract(1), FakeContract(2), FakeContract(3)]
    execution_service = FakeReminderExecutionService(fail_ids={2})
    run_repo = FakeSchedulerRunRepository()
    event_repo = FakeSchedulerEventRepository()

    _install(monkeypatch, contracts, execution_service, run_repo, event_repo)

    scheduler_module.send_daily_reminders()

    # All three contracts were attempted despite c2 failing
    assert execution_service.executed == [1, 2, 3]

    statuses = {(e.contract_id, e.status) for e in event_repo.events}
    assert statuses == {(1, "SENT"), (2, "FAILED"), (3, "SENT")}

    failed_event = next(e for e in event_repo.events if e.contract_id == 2)
    assert failed_event.message == "reminder failed"


def test_run_counts_updated_correctly(monkeypatch):

    contracts = [FakeContract(1), FakeContract(2), FakeContract(3)]
    execution_service = FakeReminderExecutionService(fail_ids={3})
    run_repo = FakeSchedulerRunRepository()
    event_repo = FakeSchedulerEventRepository()

    _install(monkeypatch, contracts, execution_service, run_repo, event_repo)

    scheduler_module.send_daily_reminders()

    assert run_repo.run.total_contracts == 3
    assert run_repo.run.successful_count == 2
    assert run_repo.run.failed_count == 1
    assert run_repo.run.status == SchedulerRunStatus.COMPLETED


class FailingReminderService:

    def get_pending_reminders(self):

        raise RuntimeError("cannot fetch contracts")


def test_top_level_failure_marks_run_failed(monkeypatch):

    run_repo = FakeSchedulerRunRepository()
    event_repo = FakeSchedulerEventRepository()

    _stub_lock(monkeypatch)

    # A failure *outside* the per-contract loop (here, fetching contracts).
    monkeypatch.setattr(
        scheduler_module,
        "create_reminder_service",
        lambda: FailingReminderService(),
    )
    monkeypatch.setattr(
        scheduler_module,
        "create_reminder_execution_service",
        lambda: FakeReminderExecutionService(),
    )
    monkeypatch.setattr(
        scheduler_module,
        "create_scheduler_run_repository",
        lambda: run_repo,
    )
    monkeypatch.setattr(
        scheduler_module,
        "create_scheduler_event_repository",
        lambda: event_repo,
    )

    with pytest.raises(RuntimeError):
        scheduler_module.send_daily_reminders()

    # The run is marked FAILED (not left RUNNING) and timestamped.
    assert run_repo.run.status == SchedulerRunStatus.FAILED
    assert run_repo.run.completed_at is not None


def test_contract_failure_still_completes_run(monkeypatch):

    contracts = [FakeContract(1), FakeContract(2)]
    execution_service = FakeReminderExecutionService(fail_ids={2})
    run_repo = FakeSchedulerRunRepository()
    event_repo = FakeSchedulerEventRepository()

    _install(monkeypatch, contracts, execution_service, run_repo, event_repo)

    scheduler_module.send_daily_reminders()

    # Individual contract failure -> a FAILED event...
    failed_events = [e for e in event_repo.events if e.status == "FAILED"]
    assert len(failed_events) == 1
    assert failed_events[0].contract_id == 2

    # ...but the run as a whole still COMPLETES (not FAILED).
    assert run_repo.run.status == SchedulerRunStatus.COMPLETED
    assert run_repo.run.successful_count == 1
    assert run_repo.run.failed_count == 1