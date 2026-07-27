from types import SimpleNamespace

from app.services.conversation_memory_service import ConversationMemoryService
from app.models.conversation import Conversation
from app.models.conversation_message import ConversationMessage
from app.enums.conversation_status import ConversationStatus
from app.enums.message_role import MessageRole


class FakeConversationRepository:

    def __init__(self, existing=None, by_id=None):
        self.existing = existing
        self.by_id = by_id
        self.created = []
        self.updated = []
        self._next_id = 1

    def get_active_by_whatsapp_chat_id(self, whatsapp_chat_id):

        return self.existing

    def get_by_id(self, conversation_id):

        return self.by_id

    def create(self, conversation):

        conversation.id = self._next_id
        self._next_id += 1
        self.created.append(conversation)

        return conversation

    def update(self, conversation):

        self.updated.append(conversation)

        return conversation


class FakeConversationMessageRepository:

    def __init__(self, recent=None):
        self.recent = recent or []
        self.created = []

    def create(self, conversation_message):

        self.created.append(conversation_message)

        return conversation_message

    def get_recent_messages(self, conversation_id, limit=10):

        return self.recent


class FakeConversationSummaryRepository:

    def __init__(self, existing=None):
        self.existing = existing
        self.upserts = []

    def get_by_conversation_id(self, conversation_id):

        return self.existing

    def create_or_update(self, conversation_id, summary):

        self.upserts.append((conversation_id, summary))
        self.existing = SimpleNamespace(
            conversation_id=conversation_id,
            summary=summary,
        )

        return self.existing


def _service(conv_repo=None, msg_repo=None, summary_repo=None):

    return ConversationMemoryService(
        conv_repo or FakeConversationRepository(),
        msg_repo or FakeConversationMessageRepository(),
        summary_repo or FakeConversationSummaryRepository(),
    )


def test_creates_new_conversation():

    conv_repo = FakeConversationRepository(existing=None)
    service = _service(conv_repo=conv_repo)

    conversation = service.get_or_create_conversation("chat_123")

    assert len(conv_repo.created) == 1
    assert conversation.whatsapp_chat_id == "chat_123"
    assert conversation.status == ConversationStatus.ACTIVE


def test_reuses_existing_conversation():

    existing = Conversation(
        whatsapp_chat_id="chat_123",
        status=ConversationStatus.ACTIVE,
    )
    existing.id = 42

    conv_repo = FakeConversationRepository(existing=existing)
    service = _service(conv_repo=conv_repo)

    conversation = service.get_or_create_conversation("chat_123")

    assert conversation is existing
    assert conv_repo.created == []


def test_stores_user_and_assistant_messages():

    msg_repo = FakeConversationMessageRepository()
    service = _service(msg_repo=msg_repo)

    service.store_user_message(1, "I paid 100")
    service.store_assistant_message(1, "Thanks, recorded.")

    assert len(msg_repo.created) == 2

    user_msg, assistant_msg = msg_repo.created

    assert user_msg.role == MessageRole.USER
    assert user_msg.content == "I paid 100"
    assert assistant_msg.role == MessageRole.ASSISTANT
    assert assistant_msg.content == "Thanks, recorded."


def test_retrieves_recent_history_as_role_content_dicts():

    recent = [
        ConversationMessage(role=MessageRole.USER, content="I paid 100"),
        ConversationMessage(role=MessageRole.ASSISTANT, content="Thanks!"),
    ]

    service = _service(msg_repo=FakeConversationMessageRepository(recent=recent))

    history = service.get_recent_history(1)

    assert history == [
        {"role": "USER", "content": "I paid 100"},
        {"role": "ASSISTANT", "content": "Thanks!"},
    ]


def test_update_summary_delegates_to_repository():

    summary_repo = FakeConversationSummaryRepository()
    service = _service(summary_repo=summary_repo)

    service.update_summary(7, "Customer is paying weekly.")

    assert summary_repo.upserts == [(7, "Customer is paying weekly.")]


def test_get_summary_returns_text_or_none():

    with_summary = FakeConversationSummaryRepository(
        existing=SimpleNamespace(summary="Running summary")
    )
    without_summary = FakeConversationSummaryRepository(existing=None)

    assert _service(summary_repo=with_summary).get_summary(7) == "Running summary"
    assert _service(summary_repo=without_summary).get_summary(7) is None


def test_close_conversation_sets_status_closed():

    conversation = Conversation(
        whatsapp_chat_id="chat_123",
        status=ConversationStatus.ACTIVE,
    )
    conversation.id = 9

    conv_repo = FakeConversationRepository(by_id=conversation)
    service = _service(conv_repo=conv_repo)

    result = service.close_conversation(9)

    assert result.status == ConversationStatus.CLOSED
    assert conv_repo.updated == [conversation]


def test_close_conversation_missing_returns_none():

    conv_repo = FakeConversationRepository(by_id=None)
    service = _service(conv_repo=conv_repo)

    assert service.close_conversation(999) is None
    assert conv_repo.updated == []


def test_get_history_includes_summary_and_messages():

    recent = [
        ConversationMessage(role=MessageRole.USER, content="I paid 100"),
    ]
    msg_repo = FakeConversationMessageRepository(recent=recent)
    summary_repo = FakeConversationSummaryRepository(
        existing=SimpleNamespace(summary="Prior summary")
    )

    service = _service(msg_repo=msg_repo, summary_repo=summary_repo)

    history = service.get_history(1)

    assert history == {
        "summary": "Prior summary",
        "messages": [{"role": "USER", "content": "I paid 100"}],
    }