from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    func,
)

from app.models.base import Base


class ProcessedMessage(Base):

    __tablename__ = "processed_messages"

    id = Column( Integer, primary_key=True )

    message_id = Column( String(255), unique=True, nullable=False )

    source = Column( String(50), nullable=False )

    processed_at = Column( DateTime(timezone=True), server_default=func.now(), nullable=False )