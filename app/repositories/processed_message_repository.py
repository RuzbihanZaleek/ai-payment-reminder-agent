from sqlalchemy.orm import Session

from app.models.processed_message import ProcessedMessage


class ProcessedMessageRepository:

    def __init__( self, db: Session):
        self.db = db

    def exists( self, message_id: str ) -> bool:
        return (
            self.db.query(ProcessedMessage)
            .filter(ProcessedMessage.message_id == message_id)
            .first()
            is not None
        )

    def create( self, message_id: str, source: str ) -> ProcessedMessage:
        processed_message = ProcessedMessage(
            message_id=message_id,
            source=source,
        )

        self.db.add(processed_message)
        self.db.commit()
        self.db.refresh(processed_message)

        return processed_message