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
    """A durable outbound notification processed by the notification worker.

    Lifecycle: ``PENDING`` -> ``PROCESSING`` -> ``SENT`` (success) or back to
    ``PENDING`` (retry, with ``available_at`` pushed into the future) or
    ``FAILED`` (after the retry budget is exhausted). The worker only becomes
    eligible to pick a row up once ``available_at <= now`` and it is ``PENDING``,
    which is how exponential backoff between retries is enforced.
    """

    __tablename__ = "notification_outbox"

    # Status values.
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SENT = "SENT"
    FAILED = "FAILED"
    DISCARDED = "DISCARDED"  # operator gave up on a FAILED message

    id = Column( Integer, primary_key=True )

    contract_id = Column( Integer, ForeignKey("contracts.id"), nullable=True, index=True )

    agent_run_id = Column( Integer, ForeignKey("agent_runs.id"), nullable=True, index=True )

    channel = Column( String(50), nullable=False, server_default="whatsapp" )

    recipient = Column( String(255), nullable=False )

    message = Column( Text, nullable=False )

    status = Column( String(20), nullable=False, server_default="PENDING", index=True )

    # Number of delivery attempts made so far.
    attempt_count = Column( Integer, nullable=False, server_default="0" )

    # Last delivery error (for troubleshooting); never contains secrets.
    last_error = Column( Text, nullable=True )

    # When the message was successfully delivered.
    sent_at = Column( DateTime(timezone=True), nullable=True )

    # Earliest time the worker may (re)attempt this message -- drives backoff and
    # oldest-first ordering.
    available_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    created_at = Column( DateTime(timezone=True), server_default=func.now(), nullable=False )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
