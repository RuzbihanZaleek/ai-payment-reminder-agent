from app.models.scheduler_run import SchedulerRun
from app.enums.scheduler_run_status import SchedulerRunStatus


def _run(harness, status, successful, failed):
    run = SchedulerRun(
        run_type="daily_reminders",
        status=status,
        total_contracts=successful + failed,
        successful_count=successful,
        failed_count=failed,
    )
    harness.session.add(run)
    harness.session.commit()
    return run


def test_reminder_statistics_and_rates(harness):
    _run(harness, SchedulerRunStatus.COMPLETED, successful=3, failed=1)
    _run(harness, SchedulerRunStatus.COMPLETED, successful=2, failed=1)
    _run(harness, SchedulerRunStatus.FAILED, successful=0, failed=0)

    stats = harness.scheduler.get_reminder_statistics()

    assert stats["total_scheduler_runs"] == 3
    assert stats["failed_scheduler_runs"] == 1
    assert stats["total_reminders_sent"] == 5
    assert stats["total_reminders_failed"] == 2
    assert stats["delivery_rate"] == round(5 / 7, 4)
    assert stats["success_rate"] == round(2 / 3, 4)


def test_recent_failures(harness):
    _run(harness, SchedulerRunStatus.COMPLETED, 3, 0)
    _run(harness, SchedulerRunStatus.FAILED, 0, 0)

    failures = harness.scheduler.get_recent_failures()
    assert len(failures) == 1
    assert failures[0]["status"] == "FAILED"


def test_empty_scheduler(harness):
    stats = harness.scheduler.get_reminder_statistics()
    assert stats["total_scheduler_runs"] == 0
    assert stats["delivery_rate"] == 0.0
    assert stats["success_rate"] == 0.0
