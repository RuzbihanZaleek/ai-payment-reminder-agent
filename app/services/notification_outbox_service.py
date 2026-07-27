from app.core.logger import get_logger
from app.models.notification_outbox import NotificationOutbox
from app.repositories.notification_outbox_repository import (
    NotificationOutboxRepository,
)


logger = get_logger(__name__)


class NotificationOutboxService:
    """Records pending outbound notifications. It never sends anything.

    Delivery is the job of a separate relay (out of scope here); this service
    only creates the durable PENDING record the relay will pick up.
    """

    _PENDING = "PENDING"
    _SENT = "SENT"
    _FAILED = "FAILED"

    def __init__(self, repository: NotificationOutboxRepository):
        self.repository = repository

    def create_pending(
        self,
        recipient: str,
        message: str,
        contract_id: int | None = None,
        agent_run_id: int | None = None,
        channel: str = "whatsapp",
    ) -> NotificationOutbox:

        outbox = self.repository.create(
            NotificationOutbox(
                contract_id=contract_id,
                agent_run_id=agent_run_id,
                channel=channel,
                recipient=recipient,
                message=message,
                status=self._PENDING,
            )
        )

        logger.info(
            "notification_outbox_created",
            extra={
                "outbox_id": outbox.id,
                "contract_id": contract_id,
                "agent_run_id": agent_run_id,
                "channel": channel,
            },
        )

        return outbox
