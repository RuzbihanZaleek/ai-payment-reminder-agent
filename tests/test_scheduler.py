import app.scheduler as scheduler_module


class FakeContract:

    def __init__(self, contract_id):
        self.id = contract_id


class FakeReminderService:

    def __init__(self, contracts):
        self.contracts = contracts

    def get_pending_reminders(self):

        return self.contracts


class FakeReminderExecutionService:

    def __init__(self):
        self.executed = []

    def execute(self, contract):

        self.executed.append(contract)


class FakeSchedulerRun:

    def __init__(self):
        self.id = 1
        self.total_contracts = 0
        self.successful_count = 0
        self.failed_count = 0
        self.completed_at = None
        self.status = None


class FakeSchedulerRunRepository:

    def __init__(self):
        self.run = FakeSchedulerRun()

    def create(self, scheduler_run):

        return self.run

    def update_status(self, scheduler_run, status):

        scheduler_run.status = status

        return scheduler_run


class FakeSchedulerEventRepository:

    def __init__(self):
        self.events = []

    def create(self, scheduler_event):

        self.events.append(scheduler_event)

        return scheduler_event


def _install_tracking(monkeypatch):

    monkeypatch.setattr(
        scheduler_module,
        "create_scheduler_run_repository",
        lambda: FakeSchedulerRunRepository(),
    )
    monkeypatch.setattr(
        scheduler_module,
        "create_scheduler_event_repository",
        lambda: FakeSchedulerEventRepository(),
    )


def test_scheduler_calls_reminder_job(monkeypatch):

    c1 = FakeContract(1)
    c2 = FakeContract(2)

    reminder_service = FakeReminderService([c1, c2])
    execution_service = FakeReminderExecutionService()

    monkeypatch.setattr(
        scheduler_module,
        "create_reminder_service",
        lambda: reminder_service,
    )
    monkeypatch.setattr(
        scheduler_module,
        "create_reminder_execution_service",
        lambda: execution_service,
    )
    _install_tracking(monkeypatch)

    scheduler_module.send_daily_reminders()

    # Every pending contract was handed to the execution service
    assert execution_service.executed == [c1, c2]


def test_reminder_job_continues_after_failure(monkeypatch):

    c1 = FakeContract(1)
    c2 = FakeContract(2)

    reminder_service = FakeReminderService([c1, c2])

    class FailingFirst:
        def __init__(self):
            self.executed = []

        def execute(self, contract):
            self.executed.append(contract)
            if contract is c1:
                raise RuntimeError("boom")

    execution_service = FailingFirst()

    monkeypatch.setattr(
        scheduler_module,
        "create_reminder_service",
        lambda: reminder_service,
    )
    monkeypatch.setattr(
        scheduler_module,
        "create_reminder_execution_service",
        lambda: execution_service,
    )
    _install_tracking(monkeypatch)

    scheduler_module.send_daily_reminders()

    # A failure on c1 must not stop c2 from being processed
    assert execution_service.executed == [c1, c2]


def test_create_scheduler_registers_daily_job():

    scheduler = scheduler_module.create_scheduler()

    job = scheduler.get_job("send_daily_reminders")

    assert job is not None
    assert job.func is scheduler_module.send_daily_reminders


def test_scheduler_run_emits_observability_fields(monkeypatch, caplog):
    import logging

    reminder_service = FakeReminderService([FakeContract(1), FakeContract(2)])
    execution_service = FakeReminderExecutionService()

    monkeypatch.setattr(
        scheduler_module, "create_reminder_service", lambda: reminder_service
    )
    monkeypatch.setattr(
        scheduler_module,
        "create_reminder_execution_service",
        lambda: execution_service,
    )
    _install_tracking(monkeypatch)

    caplog.set_level(logging.INFO)
    scheduler_module.send_daily_reminders()

    completed = next(
        r for r in caplog.records if r.getMessage() == "scheduler_run_completed"
    )

    assert completed.scheduler_run_id == 1
    assert hasattr(completed, "correlation_id")
    assert hasattr(completed, "duration_ms")
    assert completed.processed_contract_count == 2
    assert completed.success_count == 2
    assert completed.failed_count == 0