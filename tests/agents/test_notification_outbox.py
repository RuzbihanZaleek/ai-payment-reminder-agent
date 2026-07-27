"""NotificationNode outbox mode + direct-mode compatibility."""

from app.agents.notification_node import NotificationNode
from app.agents.state import AgentState
from app.enums.trigger_type import TriggerType


class FakeNotificationService:
    def __init__(self, result=True):
        self.result = result
        self.sent = []

    def send(self, recipient, message):
        self.sent.append((recipient, message))
        return self.result


class FakeReminderLogRepository:
    def __init__(self):
        self.created = []

    def create(self, reminder_log):
        self.created.append(reminder_log)
        return reminder_log


class FakeOutboxService:
    def __init__(self):
        self.created = []

    def create_pending(self, recipient, message, contract_id=None, agent_run_id=None, channel="whatsapp"):
        record = {
            "recipient": recipient,
            "message": message,
            "contract_id": contract_id,
            "agent_run_id": agent_run_id,
            "status": "PENDING",
        }
        self.created.append(record)
        return record


def _state():
    return AgentState(
        message="hi",
        contract_id=7,
        agent_run_id=99,
        whatsapp_chat_id="chat-1",
        generated_message="Your balance is $50",
    )


def test_direct_mode_sends_and_is_unchanged():
    notifier = FakeNotificationService(result=True)
    node = NotificationNode(notifier, FakeReminderLogRepository())  # default direct

    result = node.execute(_state())

    assert notifier.sent == [("chat-1", "Your balance is $50")]
    assert result.notification_sent is True
    assert result.notification_status == "SENT"


def test_outbox_mode_creates_pending_record_and_does_not_send():
    notifier = FakeNotificationService()
    outbox = FakeOutboxService()
    node = NotificationNode(
        notifier,
        FakeReminderLogRepository(),
        notification_outbox_service=outbox,
        notification_mode="outbox",
    )

    result = node.execute(_state())

    # Nothing sent inline; a PENDING record was created instead.
    assert notifier.sent == []
    assert len(outbox.created) == 1
    assert outbox.created[0]["recipient"] == "chat-1"
    assert outbox.created[0]["contract_id"] == 7
    assert outbox.created[0]["agent_run_id"] == 99
    assert outbox.created[0]["status"] == "PENDING"
    assert result.notification_sent is False
    assert result.notification_status == "PENDING"


def test_outbox_mode_skips_when_no_message():
    outbox = FakeOutboxService()
    node = NotificationNode(
        FakeNotificationService(),
        FakeReminderLogRepository(),
        notification_outbox_service=outbox,
        notification_mode="outbox",
    )

    state = _state()
    state.generated_message = None

    result = node.execute(state)

    assert outbox.created == []
    assert result.notification_status == "SKIPPED"


def test_direct_mode_failed_send_sets_failed_status():
    node = NotificationNode(FakeNotificationService(result=False), FakeReminderLogRepository())

    result = node.execute(_state())

    assert result.notification_sent is False
    assert result.notification_status == "FAILED"
