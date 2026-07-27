from app.agents.state import AgentState
from app.agents.payment_detection_node import PaymentDetectionNode
from app.agents.confidence_checker_node import ConfidenceCheckerNode
from app.agents.contract_resolver_node import ContractResolverNode
from app.agents.approval_creation_node import ApprovalCreationNode
from app.agents.payment_creation_node import PaymentCreationNode
from app.agents.balance_update_node import BalanceUpdateNode
from app.agents.reminder_decision_node import ReminderDecisionNode
from app.agents.response_generation_node import ResponseGenerationNode
from app.agents.notification_node import NotificationNode
from app.agents.workflow_executor import WorkflowExecutor


class PaymentWorkflow:

    def __init__(
        self,
        payment_detection_node: PaymentDetectionNode,
        confidence_checker_node: ConfidenceCheckerNode,
        contract_resolver_node: ContractResolverNode,
        approval_creation_node: ApprovalCreationNode,
        payment_creation_node: PaymentCreationNode,
        balance_update_node: BalanceUpdateNode,
        reminder_decision_node: ReminderDecisionNode,
        response_generation_node: ResponseGenerationNode,
        notification_node: NotificationNode,
        workflow_executor: WorkflowExecutor,
    ):
        self.payment_detection_node = payment_detection_node
        self.confidence_checker_node = confidence_checker_node
        self.contract_resolver_node = contract_resolver_node
        self.approval_creation_node = approval_creation_node
        self.payment_creation_node = payment_creation_node
        self.balance_update_node = balance_update_node
        self.reminder_decision_node = reminder_decision_node
        self.response_generation_node = response_generation_node
        self.notification_node = notification_node
        self.workflow_executor = workflow_executor


    def process(self, state: AgentState, agent_run_id: int) -> AgentState:

        state = self._execute_node(
            agent_run_id,
            "PaymentDetectionNode",
            self.payment_detection_node,
            state,
        )

        state = self._execute_node(
            agent_run_id,
            "ConfidenceCheckerNode",
            self.confidence_checker_node,
            state,
        )

        state = self._execute_node(
            agent_run_id,
            "ContractResolverNode",
            self.contract_resolver_node,
            state,
        )

        state = self._execute_node(
            agent_run_id,
            "ApprovalCreationNode",
            self.approval_creation_node,
            state,
        )

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
