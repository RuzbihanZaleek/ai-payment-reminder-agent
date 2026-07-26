from app.agents.state import AgentState
from app.enums.reminder_decision import ReminderDecision


class ReminderDecisionNode:

    def execute(
        self,
        state: AgentState,
    ) -> AgentState:

        if state.requires_approval:
            state.decision = ReminderDecision.WAIT_FOR_APPROVAL

        elif state.remaining_amount == 0:
            state.decision = ReminderDecision.CONTRACT_COMPLETED

        elif state.payment_detection is not None:
            state.decision = ReminderDecision.NO_REMINDER

        else:
            state.decision = ReminderDecision.SEND_REMINDER

        return state
