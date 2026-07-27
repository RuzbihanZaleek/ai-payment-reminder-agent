"""Dead-letter handling for the notification outbox.

Operator-facing recovery actions over FAILED notifications: list them, requeue
one for another delivery attempt, or permanently discard it. All persistence is
delegated to the repository -- this service only exposes the operations.
"""

from app.core.logger import get_logger
from app.models.notification_outbox import NotificationOutbox
from app.repositories.notification_outbox_repository import (
    NotificationOutboxRepository,
)


logger = get_logger(__name__)


class NotificationRecoveryService:

    def __init__(self, repository: NotificationOutboxRepository):
        self.repository = repository

    def list_failed(self) -> list[NotificationOutbox]:
        return self.repository.get_failed()

    def list_pending(self) -> list[NotificationOutbox]:
        return self.repository.get_by_status(NotificationOutbox.PENDING)

    def retry(self, outbox_id: int) -> NotificationOutbox | None:
        """Requeue a FAILED notification. None if not found / not FAILED."""

        outbox = self.repository.retry_failed(outbox_id)

        if outbox is not None:
            logger.info("notification_retry_requested", extra={"outbox_id": outbox_id})

        return outbox

    def discard(self, outbox_id: int) -> NotificationOutbox | None:
        """Permanently discard a FAILED notification. None if not found / not FAILED."""

        outbox = self.repository.discard_failed(outbox_id)

        if outbox is not None:
            logger.info("notification_discarded", extra={"outbox_id": outbox_id})

        return outbox
