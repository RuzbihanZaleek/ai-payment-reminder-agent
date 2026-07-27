from sqlalchemy.orm import Session

from app.models.conversation_summary import ConversationSummary


class ConversationSummaryRepository:

    def __init__( self, db: Session):
        self.db = db

    def get_by_conversation_id( self, conversation_id: int ) -> ConversationSummary | None:
        return (
            self.db.query(ConversationSummary)
            .filter(ConversationSummary.conversation_id == conversation_id)
            .first()
        )

    def create_or_update( self, conversation_id: int, summary: str ) -> ConversationSummary:
        existing = self.get_by_conversation_id(conversation_id)

        if existing is not None:
            existing.summary = summary

            self.db.commit()
            self.db.refresh(existing)

            return existing

        created = ConversationSummary(
            conversation_id=conversation_id,
            summary=summary,
        )

        self.db.add(created)
        self.db.commit()
        self.db.refresh(created)

        return created