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
from app.enums.agent_run_status import AgentRunStatus


class AgentRun(Base):

    __tablename__ = "agent_runs"

    id = Column( Integer, primary_key=True )

    contract_id = Column( Integer, ForeignKey("contracts.id"), nullable=False )

    message_id = Column( String(255), nullable=False )

    status = Column( Enum(AgentRunStatus), nullable=False, default=AgentRunStatus.PENDING )

    current_step = Column( String(100), nullable=True )

    created_at = Column( DateTime(timezone=True), server_default=func.now(), nullable=False )

    completed_at = Column( DateTime(timezone=True), nullable=True )
