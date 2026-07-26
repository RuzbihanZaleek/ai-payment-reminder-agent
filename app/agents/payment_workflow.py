from app.agents.state import AgentState
from app.agents.payment_message_agent import PaymentMessageAgent
from app.agents.confidence_checker import ConfidenceChecker
from app.agents.payment_creation_node import PaymentCreationNode
from app.agents.balance_update_node import BalanceUpdateNode
from app.agents.reminder_decision_node import ReminderDecisionNode
from app.agents.response_generation_node import ResponseGenerationNode
from app.agents.notification_node import NotificationNode
from app.agents.workflow_executor import WorkflowExecutor


class PaymentWorkflow:

    def __init__(
        self,
        payment_agent: PaymentMessageAgent,
        confidence_checker: ConfidenceChecker,
        payment_creation_node: PaymentCreationNode,
        balance_update_node: BalanceUpdateNode,
        reminder_decision_node: ReminderDecisionNode,
        response_generation_node: ResponseGenerationNode,
        notification_node: NotificationNode,
        workflow_executor: WorkflowExecutor,
    ):
        self.payment_agent = payment_agent
        self.confidence_checker = confidence_checker
        self.payment_creation_node = payment_creation_node
        self.balance_update_node = balance_update_node
        self.reminder_decision_node = reminder_decision_node
        self.response_generation_node = response_generation_node
        self.notification_node = notification_node
        self.workflow_executor = workflow_executor


    def process(self, state: AgentState, agent_run_id: int) -> AgentState:

        detection = self.payment_agent.analyze_message(
            state.message
        )

        state.payment_detection = detection

        state = self.confidence_checker.check(state)

        state = self._execute_node(
            agent_run_id,
            "PaymentCreationNode",
            self.payment_creation_node,
            state,
        )

        state = self._execute_node(
            agent_run_id,
            "BalanceUpdateNode",
            self.balance_update_node,
            state,
        )

        state = self._execute_node(
            agent_run_id,
            "ReminderDecisionNode",
            self.reminder_decision_node,
            state,
        )

        state = self._execute_node(
            agent_run_id,
            "ResponseGenerationNode",
            self.response_generation_node,
            state,
        )

        state = self._execute_node(
            agent_run_id,
            "NotificationNode",
            self.notification_node,
            state,
        )

        # All nodes succeeded -> the run as a whole is complete.
        self.workflow_executor.mark_run_completed(agent_run_id)

        return state

    def _execute_node(
        self,
        agent_run_id: int,
        node_name: str,
        node,
        state: AgentState,
    ) -> AgentState:

        return self.workflow_executor.execute_node(
            agent_run_id,
            node_name,
            node,
            state,
        )
