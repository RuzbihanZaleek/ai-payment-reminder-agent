import app.scheduler as scheduler_module


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


def test_scheduler_calls_reminder_job(monkeypatch):

    c1 = object()
    c2 = object()

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

    scheduler_module.send_daily_reminders()

    # Every pending contract was handed to the execution service
    assert execution_service.executed == [c1, c2]


def test_reminder_job_continues_after_failure(monkeypatch):

    c1 = object()
    c2 = object()

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

    scheduler_module.send_daily_reminders()

    # A failure on c1 must not stop c2 from being processed
    assert execution_service.executed == [c1, c2]


def test_create_scheduler_registers_daily_job():

    scheduler = scheduler_module.create_scheduler()

    job = scheduler.get_job("send_daily_reminders")

    assert job is not None
    assert job.func is scheduler_module.send_daily_reminders
