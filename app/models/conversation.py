from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum,
    func,
)

from app.models.base import Base
from app.enums.conversation_status import ConversationStatus


class Conversation(Base):

    __tablename__ = "conversations"

    id = Column( Integer, primary_key=True )

    whatsapp_chat_id = Column( String(255), nullable=False )

    status = Column( Enum(ConversationStatus), nullable=False, default=ConversationStatus.ACTIVE )

    created_at = Column( DateTime(timezone=True), server_default=func.now(), nullable=False )

    updated_at = Column( DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False )