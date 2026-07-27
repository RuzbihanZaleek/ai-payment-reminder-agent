from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.enums.conversation_status import ConversationStatus


class ConversationRepository:

    def __init__( self, db: Session):
        self.db = db

    def create( self, conversation: Conversation ) -> Conversation:
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)

        return conversation

    def get_active_by_whatsapp_chat_id( self, whatsapp_chat_id: str ) -> Conversation | None:
        return (
            self.db.query(Conversation)
            .filter(Conversation.whatsapp_chat_id == whatsapp_chat_id)
            .filter(Conversation.status == ConversationStatus.ACTIVE)
            .first()
        )

    def get_by_id( self, conversation_id: int ) -> Conversation | None:
        return (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )

    def update( self, conversation: Conversation ) -> Conversation:
        self.db.commit()
        self.db.refresh(conversation)

        return conversation