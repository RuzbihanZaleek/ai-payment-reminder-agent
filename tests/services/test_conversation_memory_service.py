from app.services.conversation_memory_service import ConversationMemoryService
from app.models.conversation import Conversation
from app.models.conversation_message import ConversationMessage
from app.enums.conversation_status import ConversationStatus
from app.enums.message_role import MessageRole


class FakeConversationRepository:

    def __init__(self, existing=None):
        self.existing = existing
        self.created = []
        self._next_id = 1

    def get_active_by_whatsapp_chat_id(self, whatsapp_chat_id):

        return self.existing

    def create(self, conversation):

        conversation.id = self._next_id
        self._next_id += 1
        self.created.append(conversation)

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


def test_creates_new_conversation():

    conv_repo = FakeConversationRepository(existing=None)
    msg_repo = FakeConversationMessageRepository()

    service = ConversationMemoryService(conv_repo, msg_repo)

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
    msg_repo = FakeConversationMessageRepository()

    service = ConversationMemoryService(conv_repo, msg_repo)

    conversation = service.get_or_create_conversation("chat_123")

    assert conversation is existing
    assert conv_repo.created == []


def test_stores_user_and_assistant_messages():

    conv_repo = FakeConversationRepository()
    msg_repo = FakeConversationMessageRepository()

    service = ConversationMemoryService(conv_repo, msg_repo)

    service.store_user_message(1, "I paid 100")
    service.store_assistant_message(1, "Thanks, recorded.")

    assert len(msg_repo.created) == 2

    user_msg, assistant_msg = msg_repo.created

    assert user_msg.role == MessageRole.USER
    assert user_msg.content == "I paid 100"
    assert assistant_msg.role == MessageRole.ASSISTANT
    assert assistant_msg.content == "Thanks, recorded."


def test_retrieves_history_as_role_content_dicts():

    recent = [
        ConversationMessage(role=MessageRole.USER, content="I paid 100"),
        ConversationMessage(role=MessageRole.ASSISTANT, content="Thanks!"),
    ]

    conv_repo = FakeConversationRepository()
    msg_repo = FakeConversationMessageRepository(recent=recent)

    service = ConversationMemoryService(conv_repo, msg_repo)

    history = service.get_recent_history(1)

    assert history == [
        {"role": "USER", "content": "I paid 100"},
        {"role": "ASSISTANT", "content": "Thanks!"},
    ]