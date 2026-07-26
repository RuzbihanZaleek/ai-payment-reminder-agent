from app.agents.state import AgentState
from app.agents.payment_message_agent import PaymentMessageAgent
from app.agents.confidence_checker import ConfidenceChecker
from app.agents.payment_creation_node import PaymentCreationNode
from app.agents.balance_update_node import BalanceUpdateNode


class PaymentWorkflow:

    def __init__(
        self,
        payment_agent: PaymentMessageAgent,
        confidence_checker: ConfidenceChecker,
        payment_creation_node: PaymentCreationNode,
        balance_update_node: BalanceUpdateNode,
    ):
        self.payment_agent = payment_agent
        self.confidence_checker = confidence_checker
        self.payment_creation_node = payment_creation_node
        self.balance_update_node = balance_update_node


    def process(self, state: AgentState) -> AgentState:

        detection = self.payment_agent.analyze_message(
            state.message
        )

        state.payment_detection = detection

        state = self.confidence_checker.check(state)

        state = self.payment_creation_node.execute(state)

        state = self.balance_update_node.execute(state)

        return state
