from app.agents.state import AgentState
from app.agents.payment_message_agent import PaymentMessageAgent


class PaymentDetectionNode:

    def __init__(
        self,
        payment_agent: PaymentMessageAgent,
    ):
        self.payment_agent = payment_agent

    def execute(
        self,
        state: AgentState,
    ) -> AgentState:

        state.payment_detection = self.payment_agent.analyze_message(
            state.message
        )

        return state
