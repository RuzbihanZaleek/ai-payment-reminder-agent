from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    func,
)

from app.models.base import Base


class ReminderLog(Base):

    __tablename__ = "reminder_logs"

    id = Column( Integer, primary_key=True )

    contract_id = Column( Integer, ForeignKey("contracts.id"), nullable=False )

    sent_at = Column( DateTime(timezone=True), server_default=func.now(), nullable=False )

    message = Column( String(500), nullable=True )

    status = Column( String(50), nullable=False, server_default="SENT" )
