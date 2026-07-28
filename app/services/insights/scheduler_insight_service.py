"""Reminder/scheduler insights (read-only, system-level).

Reuses SchedulerReportingService. Scheduler data is system-level infrastructure
(not user-scoped), consistent with the reporting/analytics layer.
"""

from app.enums.scheduler_run_status import SchedulerRunStatus
from app.enums.sort_order import SortOrder
from app.repositories.filters import SchedulerRunFilter
from app.services.scheduler_reporting_service import SchedulerReportingService


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


class SchedulerInsightService:

    def __init__(self, scheduler_reporting_service: SchedulerReportingService):
        self.scheduler_reporting_service = scheduler_reporting_service

    def _stats(self) -> dict:
        return self.scheduler_reporting_service.get_scheduler_stats()

    def _recent_runs(self, page_size: int = 10, status=None) -> list:
        result = self.scheduler_reporting_service.get_recent_runs(
            SchedulerRunFilter(status=status),
            page=1,
            page_size=page_size,
            order=SortOrder.DESC,
        )
        return result.items

    def get_scheduler_summary(self) -> dict:
        return self._stats()

    def get_delivery_rate(self) -> float:
        stats = self._stats()
        attempted = stats["total_reminders_sent"] + stats["total_reminders_failed"]
        return _rate(stats["total_reminders_sent"], attempted)

    def get_success_rate(self) -> float:
        stats = self._stats()
        successful = stats["total_scheduler_runs"] - stats["failed_scheduler_runs"]
        return _rate(successful, stats["total_scheduler_runs"])

    def _run_dict(self, run) -> dict:
        return {
            "scheduler_run_id": run.id,
            "run_type": run.run_type,
            "status": run.status.value if hasattr(run.status, "value") else run.status,
            "started_at": run.started_at,
            "total_contracts": run.total_contracts,
            "successful_count": run.successful_count,
            "failed_count": run.failed_count,
        }

    def get_failed_contracts(self, limit: int = 10) -> list[dict]:
        # Recent runs that had at least one failed delivery.
        return [
            self._run_dict(r)
            for r in self._recent_runs(page_size=limit)
            if r.failed_count > 0
        ]

    def get_recent_failures(self, limit: int = 10) -> list[dict]:
        return [
            self._run_dict(r)
            for r in self._recent_runs(page_size=limit, status=SchedulerRunStatus.FAILED)
        ]

    def get_recent_activity(self, limit: int = 10) -> list[dict]:
        return [self._run_dict(r) for r in self._recent_runs(page_size=limit)]

    def get_average_daily_reminders(self) -> float:
        stats = self._stats()
        # Reminders are a daily job, so per-run ≈ per-day.
        return _rate(stats["total_reminders_sent"], stats["total_scheduler_runs"])

    def get_reminder_statistics(self) -> dict:
        stats = self._stats()
        return {
            **stats,
            "delivery_rate": self.get_delivery_rate(),
            "success_rate": self.get_success_rate(),
        }
