from app.models.scheduler_run import SchedulerRun
from app.repositories.scheduler_run_repository import SchedulerRunRepository
from app.repositories.scheduler_event_repository import SchedulerEventRepository


class SchedulerReportingService:

    def __init__(
        self,
        scheduler_run_repository: SchedulerRunRepository,
        scheduler_event_repository: SchedulerEventRepository,
    ):
        self.scheduler_run_repository = scheduler_run_repository
        self.scheduler_event_repository = scheduler_event_repository

    def get_recent_runs(self, limit: int = 20) -> list[SchedulerRun]:

        return self.scheduler_run_repository.get_recent(limit)

    def get_run_details(self, run_id: int) -> dict | None:

        run = self.scheduler_run_repository.get_by_id(run_id)

        if run is None:
            return None

        return {
            "run": run,
            "events": self.scheduler_event_repository.get_by_run_id(run_id),
        }