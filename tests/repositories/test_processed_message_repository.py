from app.repositories.processed_message_repository import (
    ProcessedMessageRepository,
)


def test_create_processed_message(db_session):

    repository = ProcessedMessageRepository(db_session)

    created = repository.create(
        message_id="wamid.create",
        source="whatsapp",
    )

    assert created.id is not None
    assert created.message_id == "wamid.create"
    assert created.source == "whatsapp"
    assert created.processed_at is not None


def test_exists_true_after_create(db_session):

    repository = ProcessedMessageRepository(db_session)

    repository.create(message_id="wamid.exists", source="whatsapp")

    assert repository.exists("wamid.exists") is True


def test_exists_false_when_absent(db_session):

    repository = ProcessedMessageRepository(db_session)

    assert repository.exists("wamid.never-seen") is False