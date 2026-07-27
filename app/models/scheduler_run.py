from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum,
    func,
)

from app.models.base import Base
from app.enums.scheduler_run_status import SchedulerRunStatus


class SchedulerRun(Base):

    __tablename__ = "scheduler_runs"

    id = Column( Integer, primary_key=True )

    run_type = Column( String(50), nullable=False )

    status = Column( Enum(SchedulerRunStatus), nullable=False )

    started_at = Column( DateTime(timezone=True), server_default=func.now(), nullable=False )

    completed_at = Column( DateTime(timezone=True), nullable=True )

    total_contracts = Column( Integer, nullable=False, default=0, server_default="0" )

    successful_count = Column( Integer, nullable=False, default=0, server_default="0" )

    failed_count = Column( Integer, nullable=False, default=0, server_default="0" )