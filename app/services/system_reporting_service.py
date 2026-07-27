"""Operational system-health reporting.

Aggregates queue/scheduler health for the operations dashboard by reusing the
existing repositories -- no business-logic duplication, no direct queries beyond
the repository methods.
"""

from datetime import datetime, timezone

from app.core.metrics import set_notification_queue_size
from app.models.notification_outbox import NotificationOutbox
from app.repositories.notification_outbox_repository import (
    NotificationOutboxRepository,
)
from app.repositories.scheduler_run_repository import SchedulerRunRepository


class SystemReportingService:

    def __init__(
        self,
        notification_outbox_repository: NotificationOutboxRepository,
        scheduler_run_repository: SchedulerRunRepository,
    ):
        self.notification_outbox_repository = notification_outbox_repository
        self.scheduler_run_repository = scheduler_run_repository

    def get_system_stats(self) -> dict:
        queue_size = self.notification_outbox_repository.count_by_status(
            NotificationOutbox.PENDING
        )
        failed_count = self.notification_outbox_repository.count_by_status(
            NotificationOutbox.FAILED
        )

        # Keep the exposed gauge aligned with the authoritative DB count.
        set_notification_queue_size(queue_size)

        oldest_pending = self.notification_outbox_repository.get_oldest_pending()
        last_run = self.scheduler_run_repository.get_last_run()

        return {
            "notification_queue_size": queue_size,
            "failed_notification_count": failed_count,
            "oldest_pending_notification_age_seconds": self._age_seconds(
                getattr(oldest_pending, "created_at", None)
            ),
            "scheduler_last_run": getattr(last_run, "started_at", None),
            "scheduler_failure_count": self.scheduler_run_repository.count_failed(),
        }

    @staticmethod
    def _age_seconds(created_at) -> float | None:
        if created_at is None:
            return None

        # created_at may be naive (SQLite) or tz-aware (Postgres); normalize.
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        return (datetime.now(timezone.utc) - created_at).total_seconds()
