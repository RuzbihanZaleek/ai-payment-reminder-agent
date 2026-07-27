from decimal import Decimal

from app.agents.payment_workflow import PaymentWorkflow
from app.agents.notification_node import NotificationNode
from app.agents.payment_detection_node import PaymentDetectionNode
from app.agents.confidence_checker_node import ConfidenceCheckerNode
from app.agents.contract_resolver_node import ContractResolverNode
from app.agents.reminder_decision_node import ReminderDecisionNode
from app.agents.response_generation_node import ResponseGenerationNode
from app.agents.state import AgentState
from app.services.payment_allocation_formatter import PaymentAllocationFormatter
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


def test_approval_required():

    node = ReminderDecisionNode()

    state = AgentState(
        message="Paid 100",
        requires_approval=True,
    )

    result = node.execute(state)

    assert result.decision == ReminderDecision.WAIT_FOR_APPROVAL


def test_contract_completed():

    node = ReminderDecisionNode()

    state = AgentState(
        message="Paid the last installment",
        requires_approval=False,
        remaining_amount=Decimal("0"),
    )

    result = node.execute(state)

    assert result.decision == ReminderDecision.CONTRACT_COMPLETED


def test_payment_received():

    node = ReminderDecisionNode()

    state = AgentState(
        message="Paid 100",
        requires_approval=False,
        remaining_amount=Decimal("650"),
        payment_detection=make_detection(),
    )

    result = node.execute(state)

    assert result.decision == ReminderDecision.NO_REMINDER


def test_send_reminder():

    node = ReminderDecisionNode()

    state = AgentState(
        message="How are things?",
        requires_approval=False,
        remaining_amount=Decimal("650"),
        payment_detection=None,
    )

    result = node.execute(state)

    assert result.decision == ReminderDecision.SEND_REMINDER


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

        state.total_paid = Decimal("350")
        state.remaining_amount = Decimal("650")

        return state


class PassthroughWorkflowExecutor:

    def execute_node(self, agent_run_id, node_name, node, state):

        return node.execute(state)

    def mark_run_completed(self, agent_run_id):
        pass


class NoopAllocationNode:

    def execute(self, state):

        return state


class NoopApprovalNode:

    def execute(self, state):

        return state


class NoopReceiptNode:

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
        NoopAllocationNode(),
        NoopApprovalNode(),
        FakePaymentCreationNode(),
        FakeBalanceUpdateNode(),
        NoopReceiptNode(),
        ReminderDecisionNode(),
        ResponseGenerationNode(PaymentAllocationFormatter()),
        NotificationNode(FakeNotificationService(), NoopReminderLogRepository()),
        PassthroughWorkflowExecutor(),
    )

    state = AgentState(
        message="I paid 100",
    )

    result = workflow.process(state, agent_run_id=1)

    # The real decision node ran last and recorded a decision.
    # Approval not required, balance remaining, payment detected -> NO_REMINDER.
    assert result.decision == ReminderDecision.NO_REMINDER
