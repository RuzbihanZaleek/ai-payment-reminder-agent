from decimal import Decimal

from app.agents.notification_node import NotificationNode
from app.agents.payment_workflow import PaymentWorkflow
from app.agents.payment_detection_node import PaymentDetectionNode
from app.agents.confidence_checker_node import ConfidenceCheckerNode
from app.agents.contract_resolver_node import ContractResolverNode
from app.agents.response_generation_node import ResponseGenerationNode
from app.agents.state import AgentState
from app.services.notification_service import FakeNotificationService
from app.enums.reminder_decision import ReminderDecision
from app.schemas.payment_detection import (
    PaymentDetectionResult,
    PaymentIntent,
)


def make_detection() -> PaymentDetectionResult:

    return PaymentDetectionResult(
        intent=PaymentIntent.PAYMENT_RECEIVED,
        amount=Decimal("100.00"),
        currency="USD",
        confidence=0.95,
    )


def test_approval_message():

    node = ResponseGenerationNode()

    state = AgentState(
        message="I paid",
        decision=ReminderDecision.WAIT_FOR_APPROVAL,
    )

    result = node.execute(state)

    assert result.generated_message == (
        "Thanks. I received your payment details.\n"
        "They are currently pending approval.\n"
        "I'll update the balance once it is confirmed."
    )


def test_completed_message():

    node = ResponseGenerationNode()

    state = AgentState(
        message="Final payment",
        decision=ReminderDecision.CONTRACT_COMPLETED,
    )

    result = node.execute(state)

    assert result.generated_message == (
        "Congratulations! Your contract has been fully paid. Thank you."
    )


def test_payment_received_message():

    node = ResponseGenerationNode()

    state = AgentState(
        message="I paid 100",
        decision=ReminderDecision.NO_REMINDER,
        payment_detection=make_detection(),
        remaining_amount=Decimal("2100"),
    )

    result = node.execute(state)

    assert result.generated_message == (
        "Thanks! I've recorded your payment of $100. "
        "Remaining balance: $2,100."
    )


def test_reminder_message():

    node = ResponseGenerationNode()

    state = AgentState(
        message="Any update?",
        decision=ReminderDecision.SEND_REMINDER,
        remaining_amount=Decimal("850"),
    )

    result = node.execute(state)

    assert result.generated_message == (
        "Friendly reminder: today's payment has not been received. "
        "Remaining balance: $850."
    )


def test_fallback_behavior():

    node = ResponseGenerationNode()

    # NO_REMINDER but neither the detected amount nor the remaining
    # balance is available -> must degrade gracefully, not crash.
    state = AgentState(
        message="I paid something",
        decision=ReminderDecision.NO_REMINDER,
        payment_detection=None,
        remaining_amount=None,
    )

    result = node.execute(state)

    assert result.generated_message == "Thanks! I've recorded your payment."
    assert "None" not in result.generated_message
    assert "$" not in result.generated_message


class FakePaymentAgent:

    def analyze_message(self, message, history=None):

        return make_detection()


class FakeConfidenceChecker:

    def check(self, state):

        state.requires_approval = False

        return state


class FakePaymentCreationNode:

    def execute(self, state):

        state.payment_id = 42

        return state


class FakeBalanceUpdateNode:

    def execute(self, state):

        state.remaining_amount = Decimal("2100")

        return state


class FakeReminderDecisionNode:

    def execute(self, state):

        state.decision = ReminderDecision.NO_REMINDER

        return state


class PassthroughWorkflowExecutor:

    def execute_node(self, agent_run_id, node_name, node, state):

        return node.execute(state)

    def mark_run_completed(self, agent_run_id):
        pass


class NoopApprovalNode:

    def execute(self, state):

        return state


class NoopReminderLogRepository:

    def create(self, reminder_log):

        return reminder_log


def test_workflow_integration():

    workflow = PaymentWorkflow(
        PaymentDetectionNode(FakePaymentAgent()),
        ConfidenceCheckerNode(FakeConfidenceChecker()),
        ContractResolverNode(),
        NoopApprovalNode(),
        FakePaymentCreationNode(),
        FakeBalanceUpdateNode(),
        FakeReminderDecisionNode(),
        ResponseGenerationNode(),
        NotificationNode(FakeNotificationService(), NoopReminderLogRepository()),
        PassthroughWorkflowExecutor(),
    )

    state = AgentState(
        message="I paid 100",
    )

    result = workflow.process(state, agent_run_id=1)

    # The real response node ran last and rendered the NO_REMINDER template.
    assert result.generated_message == (
        "Thanks! I've recorded your payment of $100. "
        "Remaining balance: $2,100."
    )
