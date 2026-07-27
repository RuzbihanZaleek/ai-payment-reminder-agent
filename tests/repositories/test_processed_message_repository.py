import uuid

from app.repositories.processed_message_repository import (
    ProcessedMessageRepository,
)


def _unique_message_id() -> str:

    # The db_session fixture doesn't roll back, and message_id is UNIQUE, so
    # each test must use an id that can't collide with rows left by prior runs.
    return f"wamid.{uuid.uuid4().hex}"


def test_create_processed_message(db_session):

    repository = ProcessedMessageRepository(db_session)

    message_id = _unique_message_id()

    created = repository.create(
        message_id=message_id,
        source="whatsapp",
    )

    assert created.id is not None
    assert created.message_id == message_id
    assert created.source == "whatsapp"
    assert created.processed_at is not None


def test_exists_true_after_create(db_session):

    repository = ProcessedMessageRepository(db_session)

    message_id = _unique_message_id()

    repository.create(message_id=message_id, source="whatsapp")

    assert repository.exists(message_id) is True


def test_exists_false_when_absent(db_session):

    repository = ProcessedMessageRepository(db_session)

    assert repository.exists(_unique_message_id()) is False