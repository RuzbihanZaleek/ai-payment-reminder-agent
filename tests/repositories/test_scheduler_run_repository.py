from app.models.scheduler_run import SchedulerRun
from app.enums.scheduler_run_status import SchedulerRunStatus
from app.repositories.scheduler_run_repository import SchedulerRunRepository


def test_create_scheduler_run(db_session):

    repository = SchedulerRunRepository(db_session)

    created = repository.create(
        SchedulerRun(
            run_type="daily_reminders",
            status=SchedulerRunStatus.RUNNING,
        )
    )

    assert created.id is not None
    assert created.status == SchedulerRunStatus.RUNNING
    assert created.started_at is not None
    assert created.total_contracts == 0
    assert created.successful_count == 0
    assert created.failed_count == 0


def test_update_status(db_session):

    repository = SchedulerRunRepository(db_session)

    run = repository.create(
        SchedulerRun(
            run_type="daily_reminders",
            status=SchedulerRunStatus.RUNNING,
        )
    )

    run.total_contracts = 5
    run.successful_count = 4
    run.failed_count = 1

    updated = repository.update_status(run, SchedulerRunStatus.COMPLETED)

    assert updated.status == SchedulerRunStatus.COMPLETED
    assert updated.total_contracts == 5
    assert updated.successful_count == 4
    assert updated.failed_count == 1


def test_get_by_id(db_session):

    repository = SchedulerRunRepository(db_session)

    run = repository.create(
        SchedulerRun(
            run_type="daily_reminders",
            status=SchedulerRunStatus.RUNNING,
        )
    )

    fetched = repository.get_by_id(run.id)

    assert fetched is not None
    assert fetched.id == run.id