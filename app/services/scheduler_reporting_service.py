from app.models.scheduler_run import SchedulerRun
from app.enums.scheduler_run_status import SchedulerRunStatus
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

    def get_scheduler_stats(self) -> dict:

        runs = self.scheduler_run_repository.get_all()

        return {
            "total_scheduler_runs": len(runs),
            "failed_scheduler_runs": sum(
                1 for r in runs if r.status == SchedulerRunStatus.FAILED
            ),
            # Reminder delivery counts aggregate the per-run tallies.
            "total_reminders_sent": sum(r.successful_count for r in runs),
            "total_reminders_failed": sum(r.failed_count for r in runs),
        }