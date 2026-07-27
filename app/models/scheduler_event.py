from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    func,
)

from app.models.base import Base


class SchedulerEvent(Base):

    __tablename__ = "scheduler_events"

    id = Column( Integer, primary_key=True )

    scheduler_run_id = Column( Integer, ForeignKey("scheduler_runs.id"), nullable=False, index=True )

    contract_id = Column( Integer, ForeignKey("contracts.id"), nullable=False, index=True )

    status = Column( String(50), nullable=False )

    message = Column( String(500), nullable=True )

    created_at = Column( DateTime(timezone=True), server_default=func.now(), nullable=False )