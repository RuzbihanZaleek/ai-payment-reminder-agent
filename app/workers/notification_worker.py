"""Notification outbox worker.

Pure orchestration: it drains due PENDING notifications and asks the
NotificationService to deliver each, translating the result into a repository
state transition (SENT / retry / FAILED). It contains no business rules -- the
delivery mechanics live in the NotificationService, persistence in the
repository, and retry timing is a fixed exponential backoff.

One failed notification never stops the rest of the batch.
"""

from dataclasses import dataclass

from app.core.logger import get_logger
from app.core.metrics import (
    record_notification_processed,
    record_notification_failed,
    record_notification_retry,
)
from app.repositories.notification_outbox_repository import (
    NotificationOutboxRepository,
)
from app.services.notification_service import NotificationService


logger = get_logger(__name__)


@dataclass
class WorkerResult:
    processed: int = 0   # attempted this run
    sent: int = 0
    retried: int = 0
    failed: int = 0


class NotificationWorker:

    def __init__(
        self,
        repository: NotificationOutboxRepository,
        notification_service: NotificationService,
        max_retries: int = 3,
        retry_base_delay_seconds: float = 2.0,
        batch_size: int = 50,
    ):
        self.repository = repository
        self.notification_service = notification_service
        self.max_retries = max_retries
        self.retry_base_delay_seconds = retry_base_delay_seconds
        self.batch_size = batch_size

    def process_batch(self) -> WorkerResult:
        pending = self.repository.get_pending(self.batch_size)

        result = WorkerResult()

        logger.info(
            "notification_worker_started",
            extra={"pending_count": len(pending), "batch_size": self.batch_size},
        )

        for notification in pending:
            # A single delivery failure must never abort the batch.
            try:
                self._process_one(notification, result)
            except Exception:
                logger.exception(
                    "notification_worker_unexpected_error",
                    extra={"outbox_id": notification.id},
                )

        return result

    def _process_one(self, notification, result: WorkerResult) -> None:
        outbox_id = notification.id
        result.processed += 1

        self.repository.mark_processing(outbox_id)

        success = self.notification_service.send(
            notification.recipient,
            notification.message,
        )

        if success:
            self.repository.mark_sent(outbox_id)
            record_notification_processed()
            result.sent += 1
            logger.info(
                "notification_sent",
                extra={"outbox_id": outbox_id, "recipient": notification.recipient},
            )
            return

        # Failure: retry with backoff until the attempt budget is exhausted.
        attempts_made = (notification.attempt_count or 0) + 1
        error = "delivery failed"

        if attempts_made >= self.max_retries:
            self.repository.mark_failed(outbox_id, error)
            record_notification_failed()
            result.failed += 1
            logger.warning(
                "notification_failed",
                extra={"outbox_id": outbox_id, "attempt_count": attempts_made},
            )
            return

        backoff = self.retry_base_delay_seconds * (2 ** (attempts_made - 1))
        self.repository.increment_retry(outbox_id, error, available_in_seconds=backoff)
        record_notification_retry()
        result.retried += 1
        logger.info(
            "notification_retry",
            extra={
                "outbox_id": outbox_id,
                "attempt_count": attempts_made,
                "backoff_seconds": backoff,
            },
        )
