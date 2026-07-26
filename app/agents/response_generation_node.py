from decimal import Decimal

from app.agents.state import AgentState
from app.enums.reminder_decision import ReminderDecision


class ResponseGenerationNode:

    def execute(
        self,
        state: AgentState,
    ) -> AgentState:

        decision = state.decision

        if decision == ReminderDecision.WAIT_FOR_APPROVAL:
            state.generated_message = (
                "Thanks. I received your payment details.\n"
                "They are currently pending approval.\n"
                "I'll update the balance once it is confirmed."
            )

        elif decision == ReminderDecision.CONTRACT_COMPLETED:
            state.generated_message = (
                "Congratulations! Your contract has been fully paid. "
                "Thank you."
            )

        elif decision == ReminderDecision.NO_REMINDER:
            state.generated_message = self._payment_received_message(state)

        elif decision == ReminderDecision.SEND_REMINDER:
            state.generated_message = self._reminder_message(state)

        else:
            state.generated_message = (
                "Thanks for your message. We'll be in touch shortly."
            )

        return state

    def _payment_received_message(
        self,
        state: AgentState,
    ) -> str:

        detection = state.payment_detection
        amount = detection.amount if detection is not None else None
        remaining = state.remaining_amount

        if amount is not None:
            intro = (
                f"Thanks! I've recorded your payment of "
                f"{self._format_money(amount)}."
            )
        else:
            intro = "Thanks! I've recorded your payment."

        if remaining is not None:
            return (
                f"{intro} Remaining balance: "
                f"{self._format_money(remaining)}."
            )

        return intro

    def _reminder_message(
        self,
        state: AgentState,
    ) -> str:

        remaining = state.remaining_amount

        base = (
            "Friendly reminder: today's payment has not been received."
        )

        if remaining is not None:
            return (
                f"{base} Remaining balance: "
                f"{self._format_money(remaining)}."
            )

        return base

    @staticmethod
    def _format_money(amount: Decimal) -> str:

        # Whole amounts render without decimals ($100, $2,100),
        # otherwise keep cents ($99.50).
        if amount == amount.to_integral_value():
            return f"${amount:,.0f}"

        return f"${amount:,.2f}"
