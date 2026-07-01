from app.agents.state import AgentState
from app.agents.payment_message_agent import PaymentMessageAgent


class PaymentWorkflow:

    def __init__(self, payment_agent: PaymentMessageAgent):
        self.payment_agent = payment_agent


    def process(self, state: AgentState) -> AgentState:

        detection = self.payment_agent.analyze_message(
            state.message
        )

        state.payment_detection = detection

        return state