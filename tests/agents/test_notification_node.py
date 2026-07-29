from datetime import date
from decimal import Decimal

from app.agents.notification_node import NotificationNode
from app.agents.payment_detection_node import PaymentDetectionNode
from app.agents.confidence_checker_node import ConfidenceCheckerNode
from app.agents.contract_resolver_node import ContractResolverNode
from app.agents.payment_workflow import PaymentWorkflow
from app.agents.state import AgentState
from app.enums.reminder_decision import ReminderDecision
from app.enums.trigger_type import TriggerType


class RecordingNotificationService:

    def __init__(self, result=True):
        self.result = result
        self.calls = []

    def send(self, recipient, message):

        self.calls.append((recipient, message))

        return self.result


class RecordingTemplateNotificationService(RecordingNotificationService):
    """A notification service that also supports reminder templates."""

    def __init__(self, result=True):
        super().__init__(result=result)
        self.template_calls = []

    def send_payment_reminder_template(self, recipient, name, amount, due_date):

        self.template_calls.append((recipient, name, amount, due_date))

        return self.result


class FakeReminderLogRepository:

    def __init__(self):
        self.created = []

    def create(self, reminder_log):

        self.created.append(reminder_log)

        return reminder_log


def test_sends_generated_message():

    service = RecordingNotificationService(result=True)

    node = NotificationNode(service, FakeReminderLogRepository())

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

    node = NotificationNode(service, FakeReminderLogRepository())

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

    node = NotificationNode(service, FakeReminderLogRepository())

    state = AgentState(
        message="Paid 100",
        whatsapp_chat_id="chat_123",
        generated_message="Thanks for your payment.",
    )

    result = node.execute(state)

    assert service.calls == [("chat_123", "Thanks for your payment.")]
    assert result.notification_sent is False
    assert result.notification_status == "FAILED"


def test_reminder_success_creates_log():

    service = RecordingNotificationService(result=True)
    log_repo = FakeReminderLogRepository()

    node = NotificationNode(service, log_repo)

    state = AgentState(
        trigger_type=TriggerType.SCHEDULED_REMINDER,
        message="",
        contract_id=7,
        whatsapp_chat_id="chat_123",
        generated_message="Friendly reminder: balance $50.",
    )

    node.execute(state)

    assert len(log_repo.created) == 1

    log = log_repo.created[0]

    assert log.contract_id == 7
    assert log.message == "Friendly reminder: balance $50."
    assert log.status == "SENT"


def test_reminder_failure_creates_no_log():

    service = RecordingNotificationService(result=False)
    log_repo = FakeReminderLogRepository()

    node = NotificationNode(service, log_repo)

    state = AgentState(
        trigger_type=TriggerType.SCHEDULED_REMINDER,
        message="",
        contract_id=7,
        whatsapp_chat_id="chat_123",
        generated_message="Friendly reminder: balance $50.",
    )

    node.execute(state)

    assert log_repo.created == []


def test_reminder_uses_template_when_configured():

    service = RecordingTemplateNotificationService(result=True)
    log_repo = FakeReminderLogRepository()

    node = NotificationNode(
        service, log_repo, reminder_template_name="payment_reminder"
    )

    state = AgentState(
        trigger_type=TriggerType.SCHEDULED_REMINDER,
        message="",
        contract_id=7,
        whatsapp_chat_id="chat_123",
        contract_name="John",
        daily_amount=Decimal("20"),
        due_date=date(2026, 7, 30),
        generated_message="Friendly reminder: balance $50.",
    )

    result = node.execute(state)

    # Delivered via the approved template, NOT as free-form text.
    assert service.template_calls == [
        ("chat_123", "John", Decimal("20"), date(2026, 7, 30))
    ]
    assert service.calls == []
    assert result.notification_status == "SENT"

    # The reminder is still logged (with the human-readable text) for dedup.
    assert len(log_repo.created) == 1
    assert log_repo.created[0].contract_id == 7


def test_reminder_falls_back_to_text_without_template():

    service = RecordingTemplateNotificationService(result=True)
    log_repo = FakeReminderLogRepository()

    # No template configured -> plain text (dev/testing behavior).
    node = NotificationNode(service, log_repo, reminder_template_name="")

    state = AgentState(
        trigger_type=TriggerType.SCHEDULED_REMINDER,
        message="",
        contract_id=7,
        whatsapp_chat_id="chat_123",
        contract_name="John",
        daily_amount=Decimal("20"),
        due_date=date(2026, 7, 30),
        generated_message="Friendly reminder: balance $50.",
    )

    node.execute(state)

    assert service.template_calls == []
    assert service.calls == [("chat_123", "Friendly reminder: balance $50.")]


def test_payment_message_never_uses_template():

    service = RecordingTemplateNotificationService(result=True)
    log_repo = FakeReminderLogRepository()

    # Template is configured, but a MESSAGE-triggered (payment) reply must stay
    # free-form text -- templates are only for proactive reminders.
    node = NotificationNode(
        service, log_repo, reminder_template_name="payment_reminder"
    )

    state = AgentState(
        trigger_type=TriggerType.MESSAGE,
        message="Paid 100",
        contract_id=7,
        whatsapp_chat_id="chat_123",
        generated_message="Thanks for your payment.",
    )

    node.execute(state)

    assert service.template_calls == []
    assert service.calls == [("chat_123", "Thanks for your payment.")]


def test_payment_notification_creates_no_log():

    service = RecordingNotificationService(result=True)
    log_repo = FakeReminderLogRepository()

    node = NotificationNode(service, log_repo)

    # A successful MESSAGE-triggered (payment) notification must NOT be logged.
    state = AgentState(
        trigger_type=TriggerType.MESSAGE,
        message="Paid 100",
        contract_id=7,
        whatsapp_chat_id="chat_123",
        generated_message="Thanks for your payment.",
    )

    node.execute(state)

    assert log_repo.created == []


class FakePaymentAgent:

    def analyze_message(self, message, history=None):

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


class NoopAllocationNode:

    def execute(self, state):

        return state


class NoopApprovalNode:

    def execute(self, state):

        return state


class NoopReceiptNode:

    def execute(self, state):

        return state


def test_workflow_integration():

    service = RecordingNotificationService(result=True)
    log_repo = FakeReminderLogRepository()

    workflow = PaymentWorkflow(
        PaymentDetectionNode(FakePaymentAgent()),
        ConfidenceCheckerNode(FakeConfidenceChecker()),
        ContractResolverNode(),
        NoopAllocationNode(),
        NoopApprovalNode(),
        FakePaymentCreationNode(),
        FakeBalanceUpdateNode(),
        NoopReceiptNode(),
        FakeReminderDecisionNode(),
        FakeResponseGenerationNode(),
        NotificationNode(service, log_repo),
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

    # This is a MESSAGE-triggered payment flow, so no reminder log is written.
    assert log_repo.created == []
