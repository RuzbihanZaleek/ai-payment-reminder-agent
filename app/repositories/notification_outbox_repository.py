from datetime import datetime, timedelta, timezone

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

    def get_pending(self, limit: int) -> list[NotificationOutbox]:
        """Return due PENDING notifications, oldest-first.

        Only rows whose ``available_at`` has passed are eligible, so a message
        scheduled for a future retry stays untouched until its backoff elapses.
        """

        now = datetime.now(timezone.utc)

        return (
            self.db.query(NotificationOutbox)
            .filter(NotificationOutbox.status == NotificationOutbox.PENDING)
            .filter(NotificationOutbox.available_at <= now)
            .order_by(NotificationOutbox.available_at.asc())
            .limit(limit)
            .all()
        )

    def mark_processing(self, outbox_id: int) -> NotificationOutbox | None:
        return self._update(outbox_id, status=NotificationOutbox.PROCESSING)

    def mark_sent(self, outbox_id: int) -> NotificationOutbox | None:
        return self._update(
            outbox_id,
            status=NotificationOutbox.SENT,
            sent_at=datetime.now(timezone.utc),
        )

    def mark_failed(self, outbox_id: int, error: str) -> NotificationOutbox | None:
        return self._update(
            outbox_id,
            status=NotificationOutbox.FAILED,
            last_error=error,
        )

    def increment_retry(
        self,
        outbox_id: int,
        error: str,
        available_in_seconds: float = 0.0,
    ) -> NotificationOutbox | None:
        """Bump the attempt count and return the row to PENDING for a later retry."""

        outbox = self.get_by_id(outbox_id)

        if outbox is None:
            return None

        outbox.attempt_count = (outbox.attempt_count or 0) + 1
        outbox.last_error = error
        outbox.status = NotificationOutbox.PENDING
        outbox.available_at = datetime.now(timezone.utc) + timedelta(
            seconds=available_in_seconds
        )

        self.db.commit()
        self.db.refresh(outbox)

        return outbox

    def recover_stuck_processing(self, timeout_minutes: int) -> int:
        """Return long-stuck PROCESSING rows to PENDING (a crashed worker).

        Bumps ``attempt_count`` (the abandoned attempt counts) and makes them
        immediately due again. Returns how many were recovered.
        """

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
        now = datetime.now(timezone.utc)

        stuck = (
            self.db.query(NotificationOutbox)
            .filter(NotificationOutbox.status == NotificationOutbox.PROCESSING)
            .filter(NotificationOutbox.updated_at < cutoff)
            .all()
        )

        for row in stuck:
            row.status = NotificationOutbox.PENDING
            row.attempt_count = (row.attempt_count or 0) + 1
            row.available_at = now

        if stuck:
            self.db.commit()

        return len(stuck)

    def get_failed(self) -> list[NotificationOutbox]:
        return (
            self.db.query(NotificationOutbox)
            .filter(NotificationOutbox.status == NotificationOutbox.FAILED)
            .order_by(NotificationOutbox.updated_at.desc())
            .all()
        )

    def retry_failed(self, outbox_id: int) -> NotificationOutbox | None:
        """Requeue a FAILED message: FAILED -> PENDING, attempt_count reset."""

        outbox = self.get_by_id(outbox_id)

        if outbox is None or outbox.status != NotificationOutbox.FAILED:
            return None

        outbox.status = NotificationOutbox.PENDING
        outbox.attempt_count = 0
        outbox.available_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(outbox)

        return outbox

    def discard_failed(self, outbox_id: int) -> NotificationOutbox | None:
        """Permanently give up on a FAILED message: FAILED -> DISCARDED."""

        outbox = self.get_by_id(outbox_id)

        if outbox is None or outbox.status != NotificationOutbox.FAILED:
            return None

        outbox.status = NotificationOutbox.DISCARDED

        self.db.commit()
        self.db.refresh(outbox)

        return outbox

    def count_by_status(self, status: str) -> int:
        return (
            self.db.query(NotificationOutbox)
            .filter(NotificationOutbox.status == status)
            .count()
        )

    def get_oldest_pending(self) -> NotificationOutbox | None:
        return (
            self.db.query(NotificationOutbox)
            .filter(NotificationOutbox.status == NotificationOutbox.PENDING)
            .order_by(NotificationOutbox.created_at.asc())
            .first()
        )

    def _update(self, outbox_id: int, **fields) -> NotificationOutbox | None:
        outbox = self.get_by_id(outbox_id)

        if outbox is None:
            return None

        for key, value in fields.items():
            setattr(outbox, key, value)

        self.db.commit()
        self.db.refresh(outbox)

        return outbox
