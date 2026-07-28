"""WhatsApp authorization guard: reads allowed, writes/unknown denied + audited."""

from app.ai.assistant.intent import AssistantIntent
from app.services.whatsapp_authorization_service import WhatsAppAuthorizationService


class FakeAudit:
    WHATSAPP_ACTION_BLOCKED = "WHATSAPP_ACTION_BLOCKED"

    def __init__(self):
        self.records = []

    def record(self, action, **kwargs):
        self.records.append({"action": action, **kwargs})


_PHONE = "94771234567"


def test_read_only_actions_allowed():
    guard = WhatsAppAuthorizationService()
    for intent in (
        AssistantIntent.BALANCE_QUERY,
        AssistantIntent.PAYMENT_HISTORY,
        AssistantIntent.CONTRACT_STATUS,
        AssistantIntent.NEXT_PAYMENT,
        AssistantIntent.GENERAL_FINANCIAL_QUERY,
        AssistantIntent.FINANCIAL_SUMMARY,
        AssistantIntent.SHOW_CONTRACTS,
        AssistantIntent.SHOW_PAYMENTS,
        AssistantIntent.SHOW_PENDING_APPROVALS,
        AssistantIntent.CANCEL_ACTION,
        AssistantIntent.UNKNOWN,
    ):
        assert guard.authorize(_PHONE, intent)["allowed"] is True


def test_write_actions_denied():
    guard = WhatsAppAuthorizationService()
    for intent in (
        AssistantIntent.CREATE_CONTRACT,
        AssistantIntent.UPDATE_CONTRACT,
        AssistantIntent.DELETE_CONTRACT,
        AssistantIntent.APPROVE_PAYMENT,
        AssistantIntent.REJECT_PAYMENT,
        AssistantIntent.SEND_REMINDERS,
        AssistantIntent.CONFIRM_ACTION,
    ):
        decision = guard.authorize(_PHONE, intent)
        assert decision["allowed"] is False
        assert decision["reason"] == "WHATSAPP_WRITE_ACTION_DISABLED"


def test_unknown_action_rejected():
    guard = WhatsAppAuthorizationService()
    decision = guard.authorize(_PHONE, "SOMETHING_ELSE")
    assert decision["allowed"] is False
    assert decision["reason"] == "WHATSAPP_UNKNOWN_ACTION"


def test_denied_write_is_audited_with_masked_phone():
    audit = FakeAudit()
    guard = WhatsAppAuthorizationService(audit_service=audit)

    guard.authorize(_PHONE, AssistantIntent.CREATE_CONTRACT)

    assert len(audit.records) == 1
    record = audit.records[0]
    assert record["action"] == "WHATSAPP_ACTION_BLOCKED"
    assert record["metadata"]["attempted_intent"] == "CREATE_CONTRACT"
    # Phone is masked -- the raw number is never stored.
    assert record["metadata"]["phone"] == "*******4567"
    assert _PHONE not in str(record["metadata"])


def test_allowed_read_is_not_audited():
    audit = FakeAudit()
    guard = WhatsAppAuthorizationService(audit_service=audit)

    guard.authorize(_PHONE, AssistantIntent.BALANCE_QUERY)

    assert audit.records == []
