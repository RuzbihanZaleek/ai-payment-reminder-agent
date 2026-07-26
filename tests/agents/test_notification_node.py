from app.agents.notification_node import NotificationNode
from app.agents.payment_workflow import PaymentWorkflow
from app.agents.state import AgentState
from app.enums.reminder_decision import ReminderDecision


class RecordingNotificationService:

    def __init__(self, result=True):
        self.result = result
        self.calls = []

    def send(self, recipient, message):

        self.calls.append((recipient, message))

        return self.result


def test_sends_generated_message():

    service = RecordingNotificationService(result=True)

    node = NotificationNode(service)

    state = AgentState(
        message="Paid 100",
        whatsapp_chat_id="chat_123",
        generated_message="Thanks for your payment.",
    )

    result = node.execute(state)

    assert service.calls == [("chat_123", "Thanks for your payment.")]
    assert result.notification_sent is True
    assert result.notification_status == "SENT"


def test_skips_when_message_missing():

    service = RecordingNotificationService(result=True)

    node = NotificationNode(service)

    state = AgentState(
        message="Paid 100",
        whatsapp_chat_id="chat_123",
        generated_message=None,
    )

    result = node.execute(state)

    assert service.calls == []
    assert result.notification_sent is False
    assert result.notification_status == "SKIPPED"


def test_handles_failed_notification_service():

    service = RecordingNotificationService(result=False)

    node = NotificationNode(service)

    state = AgentState(
        message="Paid 100",
        whatsapp_chat_id="chat_123",
        generated_message="Thanks for your payment.",
    )

    result = node.execute(state)

    assert service.calls == [("chat_123", "Thanks for your payment.")]
    assert result.notification_sent is False
    assert result.notification_status == "FAILED"


class FakePaymentAgent:

    def analyze_message(self, message):

        from app.schemas.payment_detection import (
            PaymentDetectionResult,
            PaymentIntent,
        )

        return PaymentDetectionResult(
            intent=PaymentIntent.PAYMENT_RECEIVED,
            amount=100,
            currency="USD",
            confidence=0.95,
        )


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

        return state


class FakeReminderDecisionNode:

    def execute(self, state):

        state.decision = ReminderDecision.NO_REMINDER

        return state


class FakeResponseGenerationNode:

    def execute(self, state):

        state.generated_message = "Thanks for your payment."

        return state


class PassthroughWorkflowExecutor:

    def execute_node(self, agent_run_id, node_name, node, state):

        return node.execute(state)

    def mark_run_completed(self, agent_run_id):
        pass


def test_workflow_integration():

    service = RecordingNotificationService(result=True)

    workflow = PaymentWorkflow(
        FakePaymentAgent(),
        FakeConfidenceChecker(),
        FakePaymentCreationNode(),
        FakeBalanceUpdateNode(),
        FakeReminderDecisionNode(),
        FakeResponseGenerationNode(),
        NotificationNode(service),
        PassthroughWorkflowExecutor(),
    )

    state = AgentState(
        message="I paid 100",
        whatsapp_chat_id="chat_123",
    )

    result = workflow.process(state, agent_run_id=1)

    # The real notification node ran last and delivered the message.
    assert service.calls == [("chat_123", "Thanks for your payment.")]
    assert result.notification_sent is True
    assert result.notification_status == "SENT"
