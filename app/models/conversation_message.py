from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Enum,
    func,
)

from app.models.base import Base
from app.enums.message_role import MessageRole


class ConversationMessage(Base):

    __tablename__ = "conversation_messages"

    id = Column( Integer, primary_key=True )

    conversation_id = Column( Integer, ForeignKey("conversations.id"), nullable=False )

    role = Column( Enum(MessageRole), nullable=False )

    content = Column( Text, nullable=False )

    created_at = Column( DateTime(timezone=True), server_default=func.now(), nullable=False )