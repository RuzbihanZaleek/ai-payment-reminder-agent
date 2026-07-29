from app.agents.state import AgentState
from app.enums.trigger_type import TriggerType
from app.models.reminder_log import ReminderLog
from app.repositories.reminder_log_repository import ReminderLogRepository
from app.services.notification_service import NotificationService


class NotificationNode:
    """Delivers the generated message.

    Two modes (selected by ``notification_mode``, default ``direct``):

    - ``direct``: send via the notification service inline (original behavior).
    - ``outbox``: record a PENDING NotificationOutbox row and return -- an
      out-of-band relay delivers it later, so a provider outage never fails the
      workflow.
    """

    def __init__(
        self,
        notification_service: NotificationService,
        reminder_log_repository: ReminderLogRepository,
        notification_outbox_service=None,
        notification_mode: str = "direct",
        reminder_template_name: str = "",
    ):
        self.notification_service = notification_service
        self.reminder_log_repository = reminder_log_repository
        self.notification_outbox_service = notification_outbox_service
        self.notification_mode = notification_mode
        self.reminder_template_name = reminder_template_name

    def execute(
        self,
        state: AgentState,
    ) -> AgentState:

        # Nothing to deliver if no message was generated
        if state.generated_message is None:
            state.notification_sent = False
            state.notification_status = "SKIPPED"

            return state

        if (
            self.notification_mode == "outbox"
            and self.notification_outbox_service is not None
        ):
            return self._execute_outbox(state)

        return self._execute_direct(state)

    def _execute_direct(self, state: AgentState) -> AgentState:

        success = self._deliver(state)

        if success:
            state.notification_sent = True
            state.notification_status = "SENT"
        else:
            state.notification_sent = False
            state.notification_status = "FAILED"

        self._maybe_log_reminder(state)

        return state

    def _deliver(self, state: AgentState) -> bool:

        # Scheduled reminders are business-initiated, so they must go out as an
        # approved template when one is configured. Everything else (payment
        # confirmations, in-session replies) stays free-form text.
        if self._should_use_template(state):
            return self.notification_service.send_payment_reminder_template(
                state.whatsapp_chat_id,
                state.contract_name,
                state.daily_amount,
                state.due_date,
            )

        return self.notification_service.send(
            state.whatsapp_chat_id,
            state.generated_message,
        )

    def _should_use_template(self, state: AgentState) -> bool:

        return (
            state.trigger_type == TriggerType.SCHEDULED_REMINDER
            and bool(self.reminder_template_name)
            and hasattr(self.notification_service, "send_payment_reminder_template")
        )

    def _execute_outbox(self, state: AgentState) -> AgentState:

        # Persist a pending record; delivery (and reminder logging) happen when
        # the relay processes it, not here.
        self.notification_outbox_service.create_pending(
            recipient=state.whatsapp_chat_id,
            message=state.generated_message,
            contract_id=state.contract_id,
            agent_run_id=state.agent_run_id,
        )

        state.notification_sent = False
        state.notification_status = "PENDING"

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
