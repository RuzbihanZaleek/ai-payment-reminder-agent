from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Enum,
    func,
)

from app.models.base import Base
from app.enums.agent_event_status import AgentEventStatus


class AgentEvent(Base):

    __tablename__ = "agent_events"

    id = Column( Integer, primary_key=True )

    agent_run_id = Column( Integer, ForeignKey("agent_runs.id"), nullable=False )

    node_name = Column( String(100), nullable=False )

    status = Column( Enum(AgentEventStatus), nullable=False )

    message = Column( String(500), nullable=True )

    duration_ms = Column( Integer, nullable=True )

    created_at = Column( DateTime(timezone=True), server_default=func.now(), nullable=False )
