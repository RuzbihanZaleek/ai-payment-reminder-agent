from app.models.conversation import Conversation
from app.models.conversation_message import ConversationMessage
from app.enums.conversation_status import ConversationStatus
from app.enums.message_role import MessageRole
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.conversation_message_repository import (
    ConversationMessageRepository,
)
from app.repositories.conversation_summary_repository import (
    ConversationSummaryRepository,
)


class ConversationMemoryService:

    def __init__(
        self,
        conversation_repository: ConversationRepository,
        conversation_message_repository: ConversationMessageRepository,
        conversation_summary_repository: ConversationSummaryRepository,
    ):
        self.conversation_repository = conversation_repository
        self.conversation_message_repository = conversation_message_repository
        self.conversation_summary_repository = conversation_summary_repository

    def get_or_create_conversation(
        self,
        whatsapp_chat_id: str,
    ) -> Conversation:

        conversation = self.conversation_repository.get_active_by_whatsapp_chat_id(
            whatsapp_chat_id
        )

        if conversation is not None:
            return conversation

        return self.conversation_repository.create(
            Conversation(
                whatsapp_chat_id=whatsapp_chat_id,
                status=ConversationStatus.ACTIVE,
            )
        )

    def store_user_message(
        self,
        conversation_id: int,
        content: str,
    ) -> ConversationMessage:

        return self._store_message(conversation_id, MessageRole.USER, content)

    def store_assistant_message(
        self,
        conversation_id: int,
        content: str,
    ) -> ConversationMessage:

        return self._store_message(conversation_id, MessageRole.ASSISTANT, content)

    def get_recent_history(
        self,
        conversation_id: int,
        limit: int = 10,
    ) -> list[dict]:

        messages = self.conversation_message_repository.get_recent_messages(
            conversation_id,
            limit,
        )

        return [
            {
                "role": message.role.value
                if hasattr(message.role, "value")
                else message.role,
                "content": message.content,
            }
            for message in messages
        ]

    def get_history(
        self,
        conversation_id: int,
        limit: int = 10,
    ) -> dict:

        # Richer view: an optional running summary plus the recent messages.
        return {
            "summary": self.get_summary(conversation_id),
            "messages": self.get_recent_history(conversation_id, limit),
        }

    def get_summary(
        self,
        conversation_id: int,
    ) -> str | None:

        summary = self.conversation_summary_repository.get_by_conversation_id(
            conversation_id
        )

        return summary.summary if summary is not None else None

    def update_summary(
        self,
        conversation_id: int,
        summary: str,
    ):

        return self.conversation_summary_repository.create_or_update(
            conversation_id,
            summary,
        )

    def close_conversation(
        self,
        conversation_id: int,
    ):

        conversation = self.conversation_repository.get_by_id(conversation_id)

        if conversation is None:
            return None

        conversation.status = ConversationStatus.CLOSED

        return self.conversation_repository.update(conversation)

    def _store_message(
        self,
        conversation_id: int,
        role: MessageRole,
        content: str,
    ) -> ConversationMessage:

        return self.conversation_message_repository.create(
            ConversationMessage(
                conversation_id=conversation_id,
                role=role,
                content=content,
            )
        )