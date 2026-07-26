from app.agents.payment_workflow import PaymentWorkflow
from app.agents.payment_detection_node import PaymentDetectionNode
from app.agents.confidence_checker_node import ConfidenceCheckerNode
from app.agents.state import AgentState


class FakePaymentAgent:

    def analyze_message(self, message):

        from app.schemas.payment_detection import PaymentDetectionResult

        from app.enums.payment_detection import PaymentIntent

        return PaymentDetectionResult(
            intent=PaymentIntent.PAYMENT_RECEIVED,
            amount=100,
            currency="USD",
            confidence=0.95
        )


class FakeConfidenceChecker:

    def __init__(self):
        self.executed = False

    def check(self, state):

        self.executed = True
        state.requires_approval = False

        return state


class FakePaymentCreationNode:

    def __init__(self):
        self.executed = False

    def execute(self, state):

        self.executed = True
        state.payment_id = 42

        return state


class FakeBalanceUpdateNode:

    def __init__(self):
        self.executed = False

    def execute(self, state):

        self.executed = True
        state.total_paid = 350
        state.remaining_amount = 650

        return state


class FakeReminderDecisionNode:

    def __init__(self):
        self.executed = False

    def execute(self, state):

        self.executed = True

        return state


class FakeResponseGenerationNode:

    def __init__(self):
        self.executed = False

    def execute(self, state):

        self.executed = True
        state.generated_message = "response"

        return state


class FakeNotificationNode:

    def __init__(self):
        self.executed = False

    def execute(self, state):

        self.executed = True
        state.notification_sent = True
        state.notification_status = "SENT"

        return state


class FakeWorkflowExecutor:

    def __init__(self):
        self.executed_nodes = []
        self.completed_run_id = None

    def execute_node(self, agent_run_id, node_name, node, state):

        self.executed_nodes.append(node_name)

        return node.execute(state)

    def mark_run_completed(self, agent_run_id):

        self.completed_run_id = agent_run_id


def test_payment_workflow():

    confidence_checker = FakeConfidenceChecker()
    payment_creation_node = FakePaymentCreationNode()
    balance_update_node = FakeBalanceUpdateNode()
    reminder_decision_node = FakeReminderDecisionNode()
    response_generation_node = FakeResponseGenerationNode()
    notification_node = FakeNotificationNode()
    workflow_executor = FakeWorkflowExecutor()

    workflow = PaymentWorkflow(
        PaymentDetectionNode(FakePaymentAgent()),
        ConfidenceCheckerNode(confidence_checker),
        payment_creation_node,
        balance_update_node,
        reminder_decision_node,
        response_generation_node,
        notification_node,
        workflow_executor
    )

    state = AgentState(
        message="Paid 100"
    )

    result = workflow.process(state, agent_run_id=123)

    # Payment detection is added to state
    assert result.payment_detection is not None
    assert result.payment_detection.amount == 100

    # Confidence checker is executed
    assert confidence_checker.executed is True

    # Payment creation node is executed
    assert payment_creation_node.executed is True

    # Final state contains payment_id
    assert result.payment_id == 42

    # Balance update node is executed
    assert balance_update_node.executed is True

    # Final state contains updated balance
    assert result.total_paid == 350
    assert result.remaining_amount == 650

    # Reminder decision node is executed
    assert reminder_decision_node.executed is True

    # Response generation node is executed
    assert response_generation_node.executed is True
    assert result.generated_message == "response"

    # Notification node is executed
    assert notification_node.executed is True
    assert result.notification_sent is True
    assert result.notification_status == "SENT"

    # All seven steps are routed through the executor, in unchanged order
    assert workflow_executor.executed_nodes == [
        "PaymentDetectionNode",
        "ConfidenceCheckerNode",
        "PaymentCreationNode",
        "BalanceUpdateNode",
        "ReminderDecisionNode",
        "ResponseGenerationNode",
        "NotificationNode",
    ]

    # A successful workflow marks the run completed with the given run id
    assert workflow_executor.completed_run_id == 123
