"""NotificationOutboxRepository ordering + state transitions (SQLite-backed)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 -- register models
from app.models.base import Base
from app.models.notification_outbox import NotificationOutbox
from app.repositories.notification_outbox_repository import (
    NotificationOutboxRepository,
)


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def _add(session, recipient, available_at, status=NotificationOutbox.PENDING):
    row = NotificationOutbox(
        recipient=recipient,
        message="m",
        status=status,
        available_at=available_at,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def test_get_pending_orders_by_available_at_asc(session):
    now = datetime.now(timezone.utc)
    _add(session, "newer", now - timedelta(minutes=1))
    _add(session, "older", now - timedelta(minutes=10))

    repo = NotificationOutboxRepository(session)
    pending = repo.get_pending(limit=10)

    assert [r.recipient for r in pending] == ["older", "newer"]


def test_get_pending_excludes_future_and_non_pending(session):
    now = datetime.now(timezone.utc)
    _add(session, "due", now - timedelta(seconds=5))
    _add(session, "future", now + timedelta(hours=1))          # backoff not elapsed
    _add(session, "sent", now - timedelta(seconds=5), status=NotificationOutbox.SENT)

    repo = NotificationOutboxRepository(session)
    pending = repo.get_pending(limit=10)

    assert [r.recipient for r in pending] == ["due"]


def test_get_pending_respects_limit(session):
    now = datetime.now(timezone.utc)
    for i in range(5):
        _add(session, f"r{i}", now - timedelta(minutes=i + 1))

    repo = NotificationOutboxRepository(session)
    assert len(repo.get_pending(limit=3)) == 3


def test_state_transitions(session):
    now = datetime.now(timezone.utc)
    row = _add(session, "a", now - timedelta(seconds=5))
    repo = NotificationOutboxRepository(session)

    repo.mark_processing(row.id)
    assert repo.get_by_id(row.id).status == NotificationOutbox.PROCESSING

    repo.mark_sent(row.id)
    refreshed = repo.get_by_id(row.id)
    assert refreshed.status == NotificationOutbox.SENT
    assert refreshed.sent_at is not None


def test_increment_retry_reschedules_and_bumps_attempt(session):
    now = datetime.now(timezone.utc)
    row = _add(session, "a", now - timedelta(seconds=5))
    repo = NotificationOutboxRepository(session)

    repo.increment_retry(row.id, "delivery failed", available_in_seconds=120)

    refreshed = repo.get_by_id(row.id)
    assert refreshed.status == NotificationOutbox.PENDING
    assert refreshed.attempt_count == 1
    assert refreshed.last_error == "delivery failed"
    # Rescheduled into the future -> not immediately due again.
    assert repo.get_pending(limit=10) == []


def test_mark_failed_sets_error(session):
    now = datetime.now(timezone.utc)
    row = _add(session, "a", now - timedelta(seconds=5))
    repo = NotificationOutboxRepository(session)

    repo.mark_failed(row.id, "permanent")

    refreshed = repo.get_by_id(row.id)
    assert refreshed.status == NotificationOutbox.FAILED
    assert refreshed.last_error == "permanent"
