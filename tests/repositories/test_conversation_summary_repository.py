import uuid
from datetime import date

from app.models.conversation import Conversation
from app.enums.conversation_status import ConversationStatus
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.conversation_summary_repository import (
    ConversationSummaryRepository,
)


def _create_conversation(db_session) -> Conversation:

    # conversation_summaries.conversation_id is a FK -> conversations.id.
    return ConversationRepository(db_session).create(
        Conversation(
            whatsapp_chat_id=f"chat_{uuid.uuid4().hex}",
            status=ConversationStatus.ACTIVE,
        )
    )


def test_create_or_update_creates_summary(db_session):

    conversation = _create_conversation(db_session)

    repository = ConversationSummaryRepository(db_session)

    created = repository.create_or_update(conversation.id, "First summary")

    assert created.id is not None
    assert created.conversation_id == conversation.id
    assert created.summary == "First summary"


def test_get_by_conversation_id(db_session):

    conversation = _create_conversation(db_session)

    repository = ConversationSummaryRepository(db_session)

    repository.create_or_update(conversation.id, "A summary")

    fetched = repository.get_by_conversation_id(conversation.id)

    assert fetched is not None
    assert fetched.summary == "A summary"


def test_create_or_update_updates_existing(db_session):

    conversation = _create_conversation(db_session)

    repository = ConversationSummaryRepository(db_session)

    first = repository.create_or_update(conversation.id, "Original")
    second = repository.create_or_update(conversation.id, "Updated")

    # Same row is reused (one summary per conversation), content replaced.
    assert second.id == first.id
    assert second.summary == "Updated"
    assert repository.get_by_conversation_id(conversation.id).summary == "Updated"


def test_get_by_conversation_id_absent(db_session):

    conversation = _create_conversation(db_session)

    repository = ConversationSummaryRepository(db_session)

    assert repository.get_by_conversation_id(conversation.id) is None