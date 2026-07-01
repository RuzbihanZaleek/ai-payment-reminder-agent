from app.agents.state import AgentState
from app.agents.payment_message_agent import PaymentMessageAgent
from app.agents.confidence_checker import ConfidenceChecker


class PaymentWorkflow:

    def __init__(self, payment_agent: PaymentMessageAgent, confidence_checker: ConfidenceChecker):
        self.payment_agent = payment_agent
        self.confidence_checker = confidence_checker


    def process(self, state: AgentState) -> AgentState:

        detection = self.payment_agent.analyze_message(
            state.message
        )

        state.payment_detection = detection
        
        state = self.confidence_checker.check(state)

        return state