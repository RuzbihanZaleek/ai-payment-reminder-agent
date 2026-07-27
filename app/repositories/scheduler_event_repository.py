from sqlalchemy.orm import Session

from app.models.scheduler_event import SchedulerEvent


class SchedulerEventRepository:

    def __init__( self, db: Session):
        self.db = db

    def create( self, scheduler_event: SchedulerEvent ) -> SchedulerEvent:
        self.db.add(scheduler_event)
        self.db.commit()
        self.db.refresh(scheduler_event)

        return scheduler_event