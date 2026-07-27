"""NotificationOutboxService creation flow (SQLite-backed)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 -- register models
from app.models.base import Base
from app.repositories.notification_outbox_repository import (
    NotificationOutboxRepository,
)
from app.services.notification_outbox_service import NotificationOutboxService


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


def test_create_pending_persists_record(session):
    service = NotificationOutboxService(NotificationOutboxRepository(session))

    record = service.create_pending(
        recipient="15551234567",
        message="Your balance is $50",
        contract_id=None,
        agent_run_id=None,
    )

    assert record.id is not None
    assert record.status == "PENDING"
    assert record.channel == "whatsapp"
    assert record.recipient == "15551234567"


def test_pending_records_are_queryable_by_status(session):
    repo = NotificationOutboxRepository(session)
    service = NotificationOutboxService(repo)

    service.create_pending(recipient="a", message="m1")
    service.create_pending(recipient="b", message="m2")

    pending = repo.get_by_status("PENDING")
    assert len(pending) == 2
    assert {r.recipient for r in pending} == {"a", "b"}
