"""AssistantService agent flow: propose-on-write, confirm, cancel, continuation."""

from types import SimpleNamespace

from app.ai.assistant.assistant_service import AssistantService
from app.ai.assistant.intent import AssistantIntent, IntentDetectionResult
from app.ai.actions.pending_action import ActionType


class FakeMemory:
    def __init__(self):
        self.stored = []

    def get_or_create_conversation(self, key):
        return SimpleNamespace(id=1)

    def get_recent_history(self, conversation_id, limit=10):
        return []

    def store_user_message(self, conversation_id, content):
        self.stored.append(("USER", content))

    def store_assistant_message(self, conversation_id, content):
        self.stored.append(("ASSISTANT", content))


class StubLLM:
    def __init__(self):
        self.next = IntentDetectionResult(intent=AssistantIntent.UNKNOWN)
        self.detect_calls = 0
        self.generate_calls = 0

    def detect_intent(self, message, history=None):
        self.detect_calls += 1
        return self.next

    def generate(self, system_prompt, message, history, context):
        self.generate_calls += 1
        return "read-answer"


class FakeToolExecutor:
    def gather(self, intent_result, user_id):
        return {"context": {}, "tool_calls": []}


class FakeActionService:
    def __init__(self):
        self.pending = None
        self.proposed = []
        self.confirmed = 0
        self.cancelled = 0

    def get_latest_pending(self, user_id):
        return self.pending

    def propose(self, user_id, action_type, params):
        self.proposed.append((action_type, params))
        self.pending = SimpleNamespace(id=1, action_type=action_type.value)
        return {"message": f"proposed {action_type.value}. Reply YES/NO.", "created": True}

    def confirm_and_execute(self, user_id):
        self.confirmed += 1
        if self.pending is None:
            return {"success": False, "message": "There's nothing to confirm."}
        self.pending = None
        return {"success": True, "message": "Contract INV005 created successfully."}

    def cancel_latest(self, user_id):
        self.cancelled += 1
        if self.pending is None:
            return {"success": False, "message": "There's nothing to cancel."}
        self.pending = None
        return {"success": True, "message": "Action cancelled."}


def _service(llm=None, action=None):
    return AssistantService(
        FakeMemory(),
        FakeToolExecutor(),
        llm or StubLLM(),
        action_service=action or FakeActionService(),
    )


def test_write_intent_proposes_only():
    llm = StubLLM()
    llm.next = IntentDetectionResult(
        intent=AssistantIntent.CREATE_CONTRACT, person="John", amount=1200,
        daily_amount=20, phone="94771234567",
    )
    action = FakeActionService()
    service = _service(llm, action)

    result = service.chat(7, "Create a contract for John, 1200 total, 20 daily, 94771234567")

    assert result["intent"] == "CREATE_CONTRACT"
    assert "proposed CREATE_CONTRACT" in result["message"]
    # Proposed, NOT executed.
    assert action.proposed and action.proposed[0][0] == ActionType.CREATE_CONTRACT
    assert action.confirmed == 0


def test_create_contract_collects_missing_fields():
    action = FakeActionService()
    llm = StubLLM()
    service = _service(llm, action)

    # Only the name so far -> asks for the total, proposes nothing.
    llm.next = IntentDetectionResult(intent=AssistantIntent.CREATE_CONTRACT, person="John")
    r1 = service.chat(7, "create a contract for John")
    assert "total" in r1["message"].lower()
    assert action.proposed == []

    # Name + total + daily but no phone -> asks for the WhatsApp number.
    llm.next = IntentDetectionResult(
        intent=AssistantIntent.CREATE_CONTRACT, person="John", amount=1200, daily_amount=20
    )
    r2 = service.chat(7, "1200 total 20 daily")
    assert "whatsapp number" in r2["message"].lower()
    assert action.proposed == []

    # All fields incl. phone -> proposes.
    llm.next = IntentDetectionResult(
        intent=AssistantIntent.CREATE_CONTRACT, person="John", amount=1200,
        daily_amount=20, phone="94771234567",
    )
    r3 = service.chat(7, "94771234567")
    assert action.proposed and action.proposed[0][0] == ActionType.CREATE_CONTRACT


def test_bare_yes_confirms_pending_without_llm():
    action = FakeActionService()
    action.pending = SimpleNamespace(id=1, action_type="SEND_REMINDERS")
    llm = StubLLM()
    service = _service(llm, action)

    result = service.chat(7, "YES")

    assert result["intent"] == "CONFIRM_ACTION"
    assert "created successfully" in result["message"]
    assert action.confirmed == 1
    # The deterministic shortcut avoided an LLM intent call.
    assert llm.detect_calls == 0


def test_bare_no_cancels_pending():
    action = FakeActionService()
    action.pending = SimpleNamespace(id=1, action_type="SEND_REMINDERS")
    service = _service(StubLLM(), action)

    result = service.chat(7, "no")

    assert result["intent"] == "CANCEL_ACTION"
    assert result["message"] == "Action cancelled."
    assert action.cancelled == 1


def test_yes_with_no_pending_falls_through_to_read():
    action = FakeActionService()  # no pending
    llm = StubLLM()
    service = _service(llm, action)

    result = service.chat(7, "yes")

    # No pending -> not a confirmation; handled as a normal (read) message.
    assert action.confirmed == 0
    assert llm.detect_calls == 1


def test_confirm_intent_with_no_pending():
    action = FakeActionService()
    llm = StubLLM()
    llm.next = IntentDetectionResult(intent=AssistantIntent.CONFIRM_ACTION)
    service = _service(llm, action)

    result = service.chat(7, "go ahead and do it")

    assert result["message"] == "There's nothing to confirm."


def test_unsupported_write_intent():
    llm = StubLLM()
    llm.next = IntentDetectionResult(intent=AssistantIntent.DELETE_CONTRACT)
    service = _service(llm, FakeActionService())

    result = service.chat(7, "delete contract INV001")

    assert "isn't supported" in result["message"]


# --- WhatsApp channel authorization (Phase 12.1) ----------------------------

def _deny_writes():
    from app.ai.assistant.intent import AssistantIntent as AI

    blocked = {
        AI.CREATE_CONTRACT, AI.UPDATE_CONTRACT, AI.DELETE_CONTRACT,
        AI.APPROVE_PAYMENT, AI.REJECT_PAYMENT, AI.SEND_REMINDERS, AI.CONFIRM_ACTION,
    }

    def _authorize(intent):
        if intent in blocked:
            return {"allowed": False, "reason": "WHATSAPP_WRITE_ACTION_DISABLED"}
        return {"allowed": True, "reason": None}

    return _authorize


def test_whatsapp_write_intent_is_blocked():
    action = FakeActionService()
    llm = StubLLM()
    llm.next = IntentDetectionResult(
        intent=AssistantIntent.CREATE_CONTRACT, person="John", amount=1200,
        daily_amount=20, phone="94771234567",
    )
    service = _service(llm, action)

    result = service.chat(7, "create a contract for John", action_authorizer=_deny_writes())

    assert "authenticated app" in result["message"]
    assert action.proposed == []  # no PendingAction created


def test_whatsapp_read_intent_still_allowed():
    action = FakeActionService()
    llm = StubLLM()
    llm.next = IntentDetectionResult(intent=AssistantIntent.BALANCE_QUERY, person="John")
    service = _service(llm, action)

    result = service.chat(7, "how much does John owe?", action_authorizer=_deny_writes())

    # Read proceeds through the normal (LLM) path.
    assert result["message"] == "read-answer"


def test_whatsapp_confirm_is_blocked_even_with_pending():
    action = FakeActionService()
    action.pending = SimpleNamespace(id=1, action_type="SEND_REMINDERS")
    service = _service(StubLLM(), action)

    result = service.chat(7, "yes", action_authorizer=_deny_writes())

    assert "authenticated app" in result["message"]
    assert action.confirmed == 0  # not executed


def test_jwt_write_still_works_without_authorizer():
    action = FakeActionService()
    llm = StubLLM()
    llm.next = IntentDetectionResult(
        intent=AssistantIntent.CREATE_CONTRACT, person="John", amount=1200,
        daily_amount=20, phone="94771234567",
    )
    service = _service(llm, action)

    # No authorizer (JWT channel) -> write proceeds to a proposal.
    result = service.chat(7, "create a contract for John")

    assert action.proposed and action.proposed[0][0] == ActionType.CREATE_CONTRACT


def test_conversation_continuation_propose_then_confirm():
    action = FakeActionService()
    llm = StubLLM()
    service = _service(llm, action)

    # Turn 1: propose (all fields incl. phone present).
    llm.next = IntentDetectionResult(
        intent=AssistantIntent.CREATE_CONTRACT, person="John", amount=1000,
        daily_amount=10, phone="94771234567",
    )
    service.chat(7, "create a contract for John 1000 total 10 daily 94771234567")
    assert action.pending is not None

    # Turn 2: bare YES confirms the surviving pending action.
    result = service.chat(7, "yes")
    assert action.confirmed == 1
    assert "created successfully" in result["message"]
