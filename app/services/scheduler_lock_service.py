"""Distributed scheduler lock backed by a PostgreSQL session-level advisory lock.

With multiple API replicas each running the in-process scheduler, the daily
reminder job would otherwise fire once per replica. A session-level advisory
lock (`pg_try_advisory_lock`) lets exactly one replica win: the others fail to
acquire it and skip the run. The lock is tied to the DB session/connection, so
it is released explicitly (and would be released anyway if the connection drops
-- a crashed replica never holds it forever).

No Redis: Postgres already exists and advisory locks are sufficient here.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logger import get_logger


logger = get_logger(__name__)


class SchedulerLockService:

    def __init__(self, db: Session, lock_id: int):
        self.db = db
        self.lock_id = lock_id
        self._acquired = False

    def acquire(self) -> bool:
        """Try to take the advisory lock without blocking. True if acquired."""

        acquired = self.db.execute(
            text("SELECT pg_try_advisory_lock(:key)"),
            {"key": self.lock_id},
        ).scalar()

        self._acquired = bool(acquired)
        return self._acquired

    def is_owned(self) -> bool:
        """Whether this service instance currently holds the lock."""

        return self._acquired

    def release(self) -> None:
        """Release the lock if held (idempotent)."""

        if not self._acquired:
            return

        try:
            self.db.execute(
                text("SELECT pg_advisory_unlock(:key)"),
                {"key": self.lock_id},
            )
        finally:
            self._acquired = False
