"""PostgreSQL advisory-lock behaviour for the distributed scheduler lock.

These are Postgres-only (advisory locks are a server feature) and run in the
container, like the other DB-backed tests.
"""

from app.db.session import SessionLocal
from app.services.scheduler_lock_service import SchedulerLockService


# A test-specific lock id so these never clash with the real scheduler lock.
_TEST_LOCK_ID = 555_000_111


def test_lock_can_be_acquired():
    session = SessionLocal()
    lock = SchedulerLockService(session, _TEST_LOCK_ID)

    try:
        assert lock.acquire() is True
        assert lock.is_owned() is True
    finally:
        lock.release()
        session.close()


def test_second_holder_is_rejected_while_locked():
    session_a = SessionLocal()
    session_b = SessionLocal()
    lock_a = SchedulerLockService(session_a, _TEST_LOCK_ID)
    lock_b = SchedulerLockService(session_b, _TEST_LOCK_ID)

    try:
        assert lock_a.acquire() is True
        # A different connection cannot take the same advisory lock.
        assert lock_b.acquire() is False
        assert lock_b.is_owned() is False
    finally:
        lock_a.release()
        lock_b.release()
        session_a.close()
        session_b.close()


def test_lock_is_reacquirable_after_release():
    session_a = SessionLocal()
    session_b = SessionLocal()
    lock_a = SchedulerLockService(session_a, _TEST_LOCK_ID)
    lock_b = SchedulerLockService(session_b, _TEST_LOCK_ID)

    try:
        assert lock_a.acquire() is True
        lock_a.release()

        # Once released, another connection can acquire it.
        assert lock_b.acquire() is True
    finally:
        lock_a.release()
        lock_b.release()
        session_a.close()
        session_b.close()
