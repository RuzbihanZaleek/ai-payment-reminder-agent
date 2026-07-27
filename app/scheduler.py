import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.container import (
    create_reminder_service,
    create_reminder_execution_service,
    create_scheduler_run_repository,
    create_scheduler_event_repository,
)
from app.enums.scheduler_run_status import SchedulerRunStatus
from app.models.scheduler_run import SchedulerRun
from app.models.scheduler_event import SchedulerEvent


logger = logging.getLogger(__name__)


def send_daily_reminders():
    """Fetch contracts due a reminder, run each, and record the run + events.

    Pure orchestration -- the "which contracts" and "what happens" decisions
    live in ReminderService and ReminderExecutionService respectively. This
    function only records observability data around them.
    """

    reminder_service = create_reminder_service()
    reminder_execution_service = create_reminder_execution_service()
    run_repository = create_scheduler_run_repository()
    event_repository = create_scheduler_event_repository()

    scheduler_run = run_repository.create(
        SchedulerRun(
            run_type="daily_reminders",
            status=SchedulerRunStatus.RUNNING,
        )
    )

    contracts = reminder_service.get_pending_reminders()

    successful_count = 0
    failed_count = 0

    for contract in contracts:
        try:
            reminder_execution_service.execute(contract)
        except Exception as exc:
            failed_count += 1

            event_repository.create(
                SchedulerEvent(
                    scheduler_run_id=scheduler_run.id,
                    contract_id=contract.id,
                    status="FAILED",
                    message=str(exc),
                )
            )

            logger.exception(
                "Reminder execution failed for contract %s",
                getattr(contract, "id", None),
            )
            continue

        successful_count += 1

        event_repository.create(
            SchedulerEvent(
                scheduler_run_id=scheduler_run.id,
                contract_id=contract.id,
                status="SENT",
            )
        )

    scheduler_run.total_contracts = len(contracts)
    scheduler_run.successful_count = successful_count
    scheduler_run.failed_count = failed_count
    scheduler_run.completed_at = datetime.now(timezone.utc)

    run_repository.update_status(scheduler_run, SchedulerRunStatus.COMPLETED)


def create_scheduler() -> BackgroundScheduler:
    """Build a scheduler with the daily reminder job registered."""

    scheduler = BackgroundScheduler()

    scheduler.add_job(
        send_daily_reminders,
        trigger=CronTrigger(hour=9, minute=0),
        id="send_daily_reminders",
        replace_existing=True,
    )

    return scheduler
