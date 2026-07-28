import uuid
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.logger import get_logger, set_request_id
from app.core.metrics import (
    record_reminder,
    record_proactive_analysis_run,
    record_proactive_users_analyzed,
    record_proactive_risks_detected,
)
from app.db.session import SessionLocal
from app.services.scheduler_lock_service import SchedulerLockService
from app.services.alert_service import default_alert_service
from app.container import (
    create_reminder_service,
    create_reminder_execution_service,
    create_scheduler_run_repository,
    create_scheduler_event_repository,
    create_notification_worker,
    create_proactive_financial_service,
    create_financial_memory_service,
    create_audit_service,
)
from app.enums.scheduler_run_status import SchedulerRunStatus
from app.models.scheduler_run import SchedulerRun
from app.models.scheduler_event import SchedulerEvent


logger = get_logger(__name__)

_JOB_ID = "send_daily_reminders"
_NOTIFICATION_JOB_ID = "process_notification_outbox"
_PROACTIVE_JOB_ID = "run_proactive_financial_analysis"


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

        default_alert_service.notify_error(
            "Daily reminder scheduler run failed",
            scheduler_run_id=getattr(scheduler_run, "id", None),
            correlation_id=correlation_id,
        )

        raise


def _open_notification_worker_lock():
    """Open a dedicated session + advisory-lock service for the worker.

    Uses a distinct lock id from the reminder scheduler so the two never
    contend, and is overridable in tests.
    """

    session = SessionLocal()
    return (
        SchedulerLockService(session, settings.NOTIFICATION_WORKER_LOCK_ID),
        session,
    )


def process_notification_outbox():
    """Drain the notification outbox once, guarded by an advisory lock.

    Separate from the reminder job (own lock, own schedule). Only one replica's
    worker runs at a time; the rest log ``notification_worker_skipped_locked``.
    """

    lock_service, lock_session = _open_notification_worker_lock()

    try:
        if not lock_service.acquire():
            logger.info(
                "notification_worker_skipped_locked",
                extra={"lock_id": settings.NOTIFICATION_WORKER_LOCK_ID},
            )
            return

        set_request_id(f"notification-worker-{uuid.uuid4().hex}")

        worker_session = SessionLocal()
        try:
            worker = create_notification_worker(db=worker_session)
            worker.process_batch()
        finally:
            worker_session.close()
    finally:
        lock_service.release()
        lock_session.close()


def _open_proactive_lock():
    """Open a dedicated session + advisory-lock service (overridable in tests)."""

    session = SessionLocal()
    return (
        SchedulerLockService(session, settings.PROACTIVE_ANALYSIS_LOCK_ID),
        session,
    )


def run_proactive_financial_analysis():
    """Proactively analyze every user's finances and record risk signals.

    Guarded by its own advisory lock (only one replica runs it). Per-user
    failures are isolated; a top-level failure is logged/alerted but never
    propagates -- the scheduler keeps running. Read-only: it only reads via the
    insight services and writes RISK_SIGNAL memories + audit rows.
    """

    lock_service, lock_session = _open_proactive_lock()

    try:
        if not lock_service.acquire():
            logger.info(
                "proactive_analysis_skipped_locked",
                extra={"lock_id": settings.PROACTIVE_ANALYSIS_LOCK_ID},
            )
            return

        set_request_id(f"proactive-{uuid.uuid4().hex}")
        record_proactive_analysis_run()

        session = SessionLocal()
        try:
            _analyze_all_users(session)
        finally:
            session.close()
    except Exception:
        # Never crash the scheduler.
        logger.exception("proactive_analysis_failed")
        default_alert_service.notify_error("Proactive financial analysis failed")
    finally:
        lock_service.release()
        lock_session.close()


def _analyze_all_users(session):
    from app.repositories.user_repository import UserRepository
    from app.services.ai_memory import FinancialMemoryType

    proactive = create_proactive_financial_service(db=session)
    memory = create_financial_memory_service(db=session)
    audit = create_audit_service(db=session)

    users = UserRepository(session).get_all()
    total_risks = 0

    for user in users:
        # One user's failure must not stop the rest.
        try:
            analysis = proactive.analyze(user.id)
            risks = analysis["risks"]
            total_risks += len(risks)

            audit.record(
                action=audit.AI_PROACTIVE_ANALYSIS,
                user_id=user.id,
                entity_type="user",
                entity_id=user.id,
                metadata={"risk_count": len(risks)},
            )

            for risk in risks:
                # De-duplicated inside the memory service.
                memory.remember(
                    user.id, FinancialMemoryType.RISK_SIGNAL, risk, confidence_score=0.6
                )
        except Exception:
            logger.exception(
                "proactive_analysis_user_failed", extra={"user_id": user.id}
            )

    record_proactive_users_analyzed(len(users))
    record_proactive_risks_detected(total_risks)

    logger.info(
        "proactive_analysis_completed",
        extra={"users_analyzed": len(users), "risks_detected": total_risks},
    )


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

    # Independent, higher-frequency job draining the notification outbox. Kept
    # separate from the reminder job (own id, own lock, own schedule).
    if settings.NOTIFICATION_WORKER_ENABLED:
        scheduler.add_job(
            process_notification_outbox,
            trigger=IntervalTrigger(
                seconds=settings.NOTIFICATION_WORKER_INTERVAL_SECONDS,
            ),
            id=_NOTIFICATION_JOB_ID,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    # Independent proactive financial-analysis job (own id, own lock, own
    # schedule) -- does not touch the reminder scheduler behaviour.
    if settings.PROACTIVE_ANALYSIS_ENABLED:
        scheduler.add_job(
            run_proactive_financial_analysis,
            trigger=IntervalTrigger(
                seconds=settings.PROACTIVE_ANALYSIS_INTERVAL_SECONDS,
            ),
            id=_PROACTIVE_JOB_ID,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
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
