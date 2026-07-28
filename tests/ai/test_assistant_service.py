"""AssistantService flow: intent -> tools -> response, memory + observability."""

from types import SimpleNamespace

from app.ai.assistant.assistant_service import AssistantService
from app.ai.assistant.intent import AssistantIntent, IntentDetectionResult


class FakeMemory:
    def __init__(self, history=None):
        self._history = history or []
        self.created_key = None
        self.stored = []  # (role, content) in call order

    def get_or_create_conversation(self, key):
        self.created_key = key
        return SimpleNamespace(id=42)

    def get_recent_history(self, conversation_id, limit=10):
        return self._history

    def store_user_message(self, conversation_id, content):
        self.stored.append(("USER", content))

    def store_assistant_message(self, conversation_id, content):
        self.stored.append(("ASSISTANT", content))


class KeywordLLM:
    """Deterministic stand-in for the LLM (no API key)."""

    def __init__(self):
        self.generate_calls = []

    def detect_intent(self, message, history=None):
        m = message.lower()
        if "owe" in m or "remaining" in m or "still need to pay" in m:
            return IntentDetectionResult(intent=AssistantIntent.BALANCE_QUERY, person="John")
        if "history" in m or "past payments" in m:
            return IntentDetectionResult(intent=AssistantIntent.PAYMENT_HISTORY)
        return IntentDetectionResult(intent=AssistantIntent.UNKNOWN)

    def generate(self, system_prompt, message, history, context):
        self.generate_calls.append({"context": context, "history": history})
        summaries = context.get("contract_summaries")
        if summaries:
            return f"Remaining: {summaries[0]['remaining_amount']}"
        return "I don't have that information."


class FakeToolExecutor:
    def __init__(self, context):
        self._context = context
        self.gather_calls = []

    def gather(self, intent_result, user_id):
        self.gather_calls.append((intent_result.intent, user_id))
        return {"context": self._context, "tool_calls": ["ContractTool.get_active_contracts"]}


class FakeAudit:
    USER_LOGIN = "USER_LOGIN"
    ASSISTANT_QUERY = "ASSISTANT_QUERY"
    ASSISTANT_RESPONSE = "ASSISTANT_RESPONSE"

    def __init__(self):
        self.records = []

    def record(self, action, user_id=None, entity_type=None, entity_id=None, metadata=None):
        self.records.append(SimpleNamespace(action=action, user_id=user_id, metadata=metadata))


def _service(memory, llm, context, audit=None):
    return AssistantService(memory, FakeToolExecutor(context), llm, audit_service=audit)


def test_balance_query_end_to_end():
    memory = FakeMemory()
    llm = KeywordLLM()
    context = {"contract_summaries": [{"contract_id": 1, "remaining_amount": 900}]}
    service = _service(memory, llm, context)

    result = service.chat(user_id=7, message="How much does John still need to pay?")

    assert result["intent"] == "BALANCE_QUERY"
    assert result["message"] == "Remaining: 900"
    # The tool context reached the LLM (no guessing).
    assert llm.generate_calls[0]["context"] == context


def test_conversation_is_persisted_after_response():
    memory = FakeMemory()
    service = _service(memory, KeywordLLM(), {"contract_summaries": []})

    service.chat(user_id=7, message="show me the history")

    # User then assistant stored, in order, under the per-user conversation key.
    assert memory.created_key == "assistant:user:7"
    assert memory.stored[0][0] == "USER"
    assert memory.stored[0][1] == "show me the history"
    assert memory.stored[1][0] == "ASSISTANT"


def test_history_loaded_before_current_turn_stored():
    memory = FakeMemory(history=[{"role": "USER", "content": "earlier"}])
    llm = KeywordLLM()
    service = _service(memory, llm, {"contract_summaries": []})

    service.chat(user_id=7, message="anything")

    # The history handed to the LLM did NOT include the current message.
    assert llm.generate_calls[0]["history"] == [{"role": "USER", "content": "earlier"}]


def test_missing_data_yields_no_invention():
    service = _service(FakeMemory(), KeywordLLM(), {"contract_summaries": []})

    result = service.chat(user_id=7, message="How much does John owe?")

    assert result["message"] == "I don't have that information."


def test_observability_records_query_and_response():
    audit = FakeAudit()
    service = _service(FakeMemory(), KeywordLLM(), {"contract_summaries": []}, audit=audit)

    service.chat(user_id=7, message="How much does John owe?")

    actions = [r.action for r in audit.records]
    assert "ASSISTANT_QUERY" in actions
    assert "ASSISTANT_RESPONSE" in actions
    # Duration + tool calls captured; never the message content.
    response_record = next(r for r in audit.records if r.action == "ASSISTANT_RESPONSE")
    assert "duration_ms" in response_record.metadata
    assert "tool_calls" in response_record.metadata
