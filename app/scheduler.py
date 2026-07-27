import uuid
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.logger import get_logger, set_request_id
from app.core.metrics import record_reminder
from app.db.session import SessionLocal
from app.services.scheduler_lock_service import SchedulerLockService
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

_JOB_ID = "send_daily_reminders"


def _open_scheduler_lock():
    """Open a dedicated session + advisory-lock service (overridable in tests).

    The lock is session-level, so the session must stay open for the whole run;
    the caller closes it in a finally block.
    """

    session = SessionLocal()
    return SchedulerLockService(session, settings.SCHEDULER_LOCK_ID), session


def send_daily_reminders():
    """Entry point for the daily reminder job.

    Guarded by a PostgreSQL advisory lock so that, across multiple replicas,
    exactly one instance runs the reminders; the rest skip. The actual reminder
    orchestration is unchanged -- see ``_execute_daily_reminders``.
    """

    lock_service, lock_session = _open_scheduler_lock()

    try:
        if not lock_service.acquire():
            # Another replica is already running the daily reminders.
            logger.info(
                "scheduler_skipped_locked",
                extra={"lock_id": settings.SCHEDULER_LOCK_ID},
            )
            return

        _execute_daily_reminders()
    finally:
        lock_service.release()
        lock_session.close()


def _execute_daily_reminders():
    """Fetch contracts due a reminder, run each, and record the run + events.

    Pure orchestration -- the "which contracts" and "what happens" decisions
    live in ReminderService and ReminderExecutionService respectively. This
    function only records observability data around them.
    """

    reminder_service = create_reminder_service()
    reminder_execution_service = create_reminder_execution_service()
    run_repository = create_scheduler_run_repository()
    event_repository = create_scheduler_event_repository()

    # Background jobs have no HTTP request, so they mint their own correlation
    # id; every log line in this run carries it.
    correlation_id = uuid.uuid4().hex
    set_request_id(correlation_id)

    start_time = datetime.now(timezone.utc)
    scheduler_run = None

    try:
        scheduler_run = run_repository.create(
            SchedulerRun(
                run_type="daily_reminders",
                status=SchedulerRunStatus.RUNNING,
            )
        )

        logger.info(
            "scheduler_run_started",
            extra={
                "scheduler_run_id": scheduler_run.id,
                "correlation_id": correlation_id,
                "start_time": start_time.isoformat(),
            },
        )

        contracts = reminder_service.get_pending_reminders()

        successful_count = 0
        failed_count = 0

        for contract in contracts:
            # A single contract failing is expected and must not abort the run.
            try:
                reminder_execution_service.execute(contract)
            except Exception as exc:
                failed_count += 1
                record_reminder(sent=False)

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
            record_reminder(sent=True)

            event_repository.create(
                SchedulerEvent(
                    scheduler_run_id=scheduler_run.id,
                    contract_id=contract.id,
                    status="SENT",
                )
            )

        completed_at = datetime.now(timezone.utc)

        scheduler_run.total_contracts = len(contracts)
        scheduler_run.successful_count = successful_count
        scheduler_run.failed_count = failed_count
        scheduler_run.completed_at = completed_at

        run_repository.update_status(scheduler_run, SchedulerRunStatus.COMPLETED)

        logger.info(
            "scheduler_run_completed",
            extra={
                "scheduler_run_id": scheduler_run.id,
                "correlation_id": correlation_id,
                "start_time": start_time.isoformat(),
                "duration_ms": int((completed_at - start_time).total_seconds() * 1000),
                "processed_contract_count": len(contracts),
                "success_count": successful_count,
                "failed_count": failed_count,
            },
        )

    except Exception:
        # A top-level failure (e.g. fetching contracts, or a repository error)
        # marks the whole run FAILED before propagating.
        failed_at = datetime.now(timezone.utc)
        logger.exception(
            "scheduler_run_failed",
            extra={
                "scheduler_run_id": getattr(scheduler_run, "id", None),
                "correlation_id": correlation_id,
                "duration_ms": int((failed_at - start_time).total_seconds() * 1000),
            },
        )

        if scheduler_run is not None:
            scheduler_run.completed_at = failed_at
            run_repository.update_status(
                scheduler_run,
                SchedulerRunStatus.FAILED,
            )

        raise


def create_scheduler() -> BackgroundScheduler:
    """Build a scheduler with the daily reminder job registered.

    Job-safety options guarantee that a downtime window never produces a burst
    of catch-up runs:

    - ``max_instances=1``  -- never run two reminder passes concurrently.
    - ``coalesce=True``    -- collapse multiple missed fires into one.
    - ``misfire_grace_time`` -- still run a missed job within the grace window.
    """

    scheduler = BackgroundScheduler()

    scheduler.add_job(
        send_daily_reminders,
        trigger=CronTrigger(
            hour=settings.SCHEDULER_HOUR,
            minute=settings.SCHEDULER_MINUTE,
        ),
        id=_JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=settings.SCHEDULER_MISFIRE_GRACE_TIME,
    )

    return scheduler


def start_scheduler() -> BackgroundScheduler | None:
    """Create and start the scheduler once, or return None if it must not run.

    Called from the FastAPI lifespan. Skipped under testing / when disabled, and
    a start failure is logged but never propagated so the API stays alive.
    """

    if not settings.SCHEDULER_ENABLED or settings.is_testing:
        logger.info(
            "scheduler_disabled",
            extra={"app_env": settings.APP_ENV, "enabled": settings.SCHEDULER_ENABLED},
        )
        return None

    scheduler = create_scheduler()

    try:
        scheduler.start()
        logger.info("scheduler_started", extra={"job_id": _JOB_ID})
        return scheduler
    except Exception:
        logger.exception("scheduler_start_failed")
        return None


def shutdown_scheduler(scheduler: BackgroundScheduler | None) -> None:
    """Stop the scheduler cleanly if one is running."""

    if scheduler is None:
        return

    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("scheduler_stopped")
    except Exception:
        logger.exception("scheduler_shutdown_failed")
