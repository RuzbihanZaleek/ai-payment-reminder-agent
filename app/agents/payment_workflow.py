from app.agents.state import AgentState
from app.agents.payment_message_agent import PaymentMessageAgent
from app.agents.confidence_checker import ConfidenceChecker
from app.agents.payment_creation_node import PaymentCreationNode


class PaymentWorkflow:

    def __init__(
        self,
        payment_agent: PaymentMessageAgent,
        confidence_checker: ConfidenceChecker,
        payment_creation_node: PaymentCreationNode,
    ):
        self.payment_agent = payment_agent
        self.confidence_checker = confidence_checker
        self.payment_creation_node = payment_creation_node


    def process(self, state: AgentState) -> AgentState:

        detection = self.payment_agent.analyze_message(
            state.message
        )

        state.payment_detection = detection

        state = self.confidence_checker.check(state)

        state = self.payment_creation_node.execute(state)

        return state
