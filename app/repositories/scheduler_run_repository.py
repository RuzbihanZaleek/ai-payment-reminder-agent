from sqlalchemy.orm import Session

from app.models.scheduler_run import SchedulerRun


class SchedulerRunRepository:

    def __init__( self, db: Session):
        self.db = db

    def create( self, scheduler_run: SchedulerRun ) -> SchedulerRun:
        self.db.add(scheduler_run)
        self.db.commit()
        self.db.refresh(scheduler_run)

        return scheduler_run

    def update_status( self, scheduler_run: SchedulerRun, status ) -> SchedulerRun:
        scheduler_run.status = status

        self.db.commit()
        self.db.refresh(scheduler_run)

        return scheduler_run

    def get_by_id( self, scheduler_run_id: int ) -> SchedulerRun | None:
        return (
            self.db.query(SchedulerRun)
            .filter(SchedulerRun.id == scheduler_run_id)
            .first()
        )

    def get_recent( self, limit: int = 20 ) -> list[SchedulerRun]:
        return (
            self.db.query(SchedulerRun)
            .order_by(SchedulerRun.id.desc())
            .limit(limit)
            .all()
        )

    def get_all( self ) -> list[SchedulerRun]:
        return (
            self.db.query(SchedulerRun)
            .all()
        )