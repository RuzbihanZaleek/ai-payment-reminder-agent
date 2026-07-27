from sqlalchemy.orm import Session

from app.models.conversation_message import ConversationMessage


class ConversationMessageRepository:

    def __init__( self, db: Session):
        self.db = db

    def create( self, conversation_message: ConversationMessage ) -> ConversationMessage:
        self.db.add(conversation_message)
        self.db.commit()
        self.db.refresh(conversation_message)

        return conversation_message

    def get_recent_messages( self, conversation_id: int, limit: int = 10 ) -> list[ConversationMessage]:
        rows = (
            self.db.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.id.desc())
            .limit(limit)
            .all()
        )

        # Return in chronological order (oldest first) for conversation context.
        return list(reversed(rows))