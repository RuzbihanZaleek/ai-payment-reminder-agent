import uuid

from app.models.conversation import Conversation
from app.enums.conversation_status import ConversationStatus
from app.repositories.conversation_repository import ConversationRepository


def _chat_id() -> str:

    # The db_session fixture doesn't roll back; a unique chat id per test keeps
    # get_active_by_whatsapp_chat_id from matching rows left by prior runs.
    return f"chat_{uuid.uuid4().hex}"


def test_create_conversation(db_session):

    repository = ConversationRepository(db_session)

    created = repository.create(
        Conversation(
            whatsapp_chat_id=_chat_id(),
            status=ConversationStatus.ACTIVE,
        )
    )

    assert created.id is not None
    assert created.status == ConversationStatus.ACTIVE
    assert created.created_at is not None


def test_get_active_by_whatsapp_chat_id(db_session):

    repository = ConversationRepository(db_session)

    chat_id = _chat_id()

    created = repository.create(
        Conversation(
            whatsapp_chat_id=chat_id,
            status=ConversationStatus.ACTIVE,
        )
    )

    fetched = repository.get_active_by_whatsapp_chat_id(chat_id)

    assert fetched is not None
    assert fetched.id == created.id


def test_get_active_ignores_closed_conversation(db_session):

    repository = ConversationRepository(db_session)

    chat_id = _chat_id()

    repository.create(
        Conversation(
            whatsapp_chat_id=chat_id,
            status=ConversationStatus.CLOSED,
        )
    )

    assert repository.get_active_by_whatsapp_chat_id(chat_id) is None


def test_update_conversation(db_session):

    repository = ConversationRepository(db_session)

    conversation = repository.create(
        Conversation(
            whatsapp_chat_id=_chat_id(),
            status=ConversationStatus.ACTIVE,
        )
    )

    conversation.status = ConversationStatus.CLOSED

    updated = repository.update(conversation)

    assert updated.status == ConversationStatus.CLOSED