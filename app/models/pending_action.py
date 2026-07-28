from sqlalchemy import (
    Column,
    Integer,
    String,
    JSON,
    DateTime,
    ForeignKey,
    func,
)

from app.models.base import Base


class PendingAction(Base):
    """A write action proposed by the AI agent, awaiting explicit user confirmation.

    Nothing is executed when this row is created -- it only records the intent.
    Execution happens only after the user confirms, and exactly once (status
    moves PENDING_CONFIRMATION -> EXECUTED). Tenant-scoped by ``user_id``.
    """

    __tablename__ = "pending_actions"

    id = Column( Integer, primary_key=True )

    user_id = Column( Integer, ForeignKey("users.id"), nullable=False, index=True )

    action_type = Column( String(50), nullable=False )

    # The parameters needed to execute the action (never secrets).
    payload_json = Column( JSON, nullable=True )

    status = Column( String(30), nullable=False, server_default="PENDING_CONFIRMATION", index=True )

    created_at = Column( DateTime(timezone=True), server_default=func.now(), nullable=False )

    expires_at = Column( DateTime(timezone=True), nullable=False )
