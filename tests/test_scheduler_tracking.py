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


def _install(monkeypatch, contracts, execution_service, run_repo, event_repo):

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