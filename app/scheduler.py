import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.container import (
    create_reminder_service,
    create_reminder_execution_service,
)


logger = logging.getLogger(__name__)


def send_daily_reminders():
    """Fetch contracts due a reminder and run the workflow for each.

    Pure orchestration -- the "which contracts" and "what happens" decisions
    live in ReminderService and ReminderExecutionService respectively.
    """

    reminder_service = create_reminder_service()
    reminder_execution_service = create_reminder_execution_service()

    contracts = reminder_service.get_pending_reminders()

    for contract in contracts:
        try:
            reminder_execution_service.execute(contract)
        except Exception:
            logger.exception(
                "Reminder execution failed for contract %s",
                getattr(contract, "id", None),
            )


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
