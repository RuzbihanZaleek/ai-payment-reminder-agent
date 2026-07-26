from app.agents.state import AgentState
from app.services.notification_service import NotificationService


class NotificationNode:

    def __init__(
        self,
        notification_service: NotificationService,
    ):
        self.notification_service = notification_service

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

        return state
