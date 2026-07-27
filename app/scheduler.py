from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.logger import get_logger, set_request_id
from app.container import (
    create_reminder_service,
    create_reminder_execution_service,
    create_scheduler_run_repository,
    create_scheduler_event_repository,
)
from app.enums.scheduler_run_status import SchedulerRunStatus
from app.models.scheduler_run import SchedulerRun
from app.models.scheduler_event import SchedulerEvent


logger = get_logger(__name__)


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

    scheduler_run = None

    try:
        scheduler_run = run_repository.create(
            SchedulerRun(
                run_type="daily_reminders",
                status=SchedulerRunStatus.RUNNING,
            )
        )

        # Correlate every log line emitted during this background run (there is
        # no HTTP request to carry a request id).
        set_request_id(f"scheduler-run-{scheduler_run.id}")

        logger.info("scheduler_run_started", extra={"scheduler_run_id": scheduler_run.id})

        contracts = reminder_service.get_pending_reminders()

        successful_count = 0
        failed_count = 0

        for contract in contracts:
            # A single contract failing is expected and must not abort the run.
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

        logger.info(
            "scheduler_run_completed",
            extra={
                "scheduler_run_id": scheduler_run.id,
                "total_contracts": len(contracts),
                "successful_count": successful_count,
                "failed_count": failed_count,
            },
        )

    except Exception:
        # A top-level failure (e.g. fetching contracts, or a repository error)
        # marks the whole run FAILED before propagating.
        logger.exception("Scheduler run failed")

        if scheduler_run is not None:
            scheduler_run.completed_at = datetime.now(timezone.utc)
            run_repository.update_status(
                scheduler_run,
                SchedulerRunStatus.FAILED,
            )

        raise


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
