from app.repositories.reminder_log_repository import ReminderLogRepository


class ReminderReportingService:

    def __init__(
        self,
        reminder_log_repository: ReminderLogRepository,
    ):
        self.reminder_log_repository = reminder_log_repository

    def get_reminder_stats(self) -> dict:

        return {
            "total_reminders_logged": len(self.reminder_log_repository.get_all()),
        }