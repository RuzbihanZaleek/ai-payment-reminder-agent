from app.services.reminder_reporting_service import ReminderReportingService
from app.services.scheduler_reporting_service import SchedulerReportingService


class ReminderAnalyticsService:

    def __init__(
        self,
        reminder_reporting_service: ReminderReportingService,
        scheduler_reporting_service: SchedulerReportingService,
    ):
        self.reminder_reporting_service = reminder_reporting_service
        self.scheduler_reporting_service = scheduler_reporting_service

    def get_reminder_analytics(self) -> dict:

        reminder_stats = self.reminder_reporting_service.get_reminder_stats()
        scheduler_stats = self.scheduler_reporting_service.get_scheduler_stats()

        sent = scheduler_stats["total_reminders_sent"]
        failed = scheduler_stats["total_reminders_failed"]
        attempted = sent + failed

        delivery_rate = float(sent / attempted) if attempted else 0.0

        return {
            "total_reminders_logged": reminder_stats["total_reminders_logged"],
            "total_reminders_sent": sent,
            "total_reminders_failed": failed,
            "delivery_rate": round(delivery_rate, 4),
        }