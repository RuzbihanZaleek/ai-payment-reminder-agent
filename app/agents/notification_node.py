from app.agents.state import AgentState
from app.enums.trigger_type import TriggerType
from app.models.reminder_log import ReminderLog
from app.repositories.reminder_log_repository import ReminderLogRepository
from app.services.notification_service import NotificationService


class NotificationNode:

    def __init__(
        self,
        notification_service: NotificationService,
        reminder_log_repository: ReminderLogRepository,
    ):
        self.notification_service = notification_service
        self.reminder_log_repository = reminder_log_repository

    def execute(
        self,
        state: AgentState,
    ) -> AgentState:

        # Nothing to deliver if no message was generated
        if state.generated_message is None:
            state.notification_sent = False
            state.notification_status = "SKIPPED"

            return state

        success = self.notification_service.send(
            state.whatsapp_chat_id,
            state.generated_message,
        )

        if success:
            state.notification_sent = True
            state.notification_status = "SENT"
        else:
            state.notification_sent = False
            state.notification_status = "FAILED"

        self._maybe_log_reminder(state)

        return state

    def _maybe_log_reminder(self, state: AgentState) -> None:

        # Only successful *scheduled reminders* are logged -- never failed
        # deliveries, and never payment-triggered notifications.
        if not state.notification_sent:
            return

        if state.trigger_type != TriggerType.SCHEDULED_REMINDER:
            return

        self.reminder_log_repository.create(
            ReminderLog(
                contract_id=state.contract_id,
                message=state.generated_message,
                status="SENT",
            )
        )
