from sqlalchemy import (
    Column,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    func,
)

from app.models.base import Base


class ConversationSummary(Base):

    __tablename__ = "conversation_summaries"

    id = Column( Integer, primary_key=True )

    conversation_id = Column( Integer, ForeignKey("conversations.id"), unique=True, nullable=False )

    summary = Column( Text, nullable=False )

    created_at = Column( DateTime(timezone=True), server_default=func.now(), nullable=False )

    updated_at = Column( DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False )