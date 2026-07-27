from sqlalchemy.orm import Session

from app.models.notification_outbox import NotificationOutbox


class NotificationOutboxRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, outbox: NotificationOutbox) -> NotificationOutbox:
        self.db.add(outbox)
        self.db.commit()
        self.db.refresh(outbox)

        return outbox

    def get_by_id(self, outbox_id: int) -> NotificationOutbox | None:
        return (
            self.db.query(NotificationOutbox)
            .filter(NotificationOutbox.id == outbox_id)
            .first()
        )

    def get_by_status(self, status: str) -> list[NotificationOutbox]:
        return (
            self.db.query(NotificationOutbox)
            .filter(NotificationOutbox.status == status)
            .all()
        )
