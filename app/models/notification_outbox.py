from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    func,
)

from app.models.base import Base


class NotificationOutbox(Base):
    """A durable, pending outbound notification.

    In "outbox" mode the workflow records one of these instead of calling the
    WhatsApp API inline; an out-of-band relay would later read PENDING rows and
    deliver them, flipping status to SENT/FAILED. This decouples delivery from
    workflow execution so a transient provider outage never fails the workflow.
    """

    __tablename__ = "notification_outbox"

    id = Column( Integer, primary_key=True )

    contract_id = Column( Integer, ForeignKey("contracts.id"), nullable=True, index=True )

    agent_run_id = Column( Integer, ForeignKey("agent_runs.id"), nullable=True, index=True )

    channel = Column( String(50), nullable=False, server_default="whatsapp" )

    recipient = Column( String(255), nullable=False )

    message = Column( Text, nullable=False )

    # PENDING -> SENT | FAILED
    status = Column( String(20), nullable=False, server_default="PENDING", index=True )

    created_at = Column( DateTime(timezone=True), server_default=func.now(), nullable=False )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
