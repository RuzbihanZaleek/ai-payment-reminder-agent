"""Intent schema + entity extraction shape."""

from app.ai.assistant.intent import AssistantIntent, IntentDetectionResult


def test_intent_defaults_to_unknown():
    result = IntentDetectionResult()
    assert result.intent == AssistantIntent.UNKNOWN
    assert result.person is None
    assert result.contract_reference is None


def test_all_intents_present():
    assert {i.value for i in AssistantIntent} == {
        "CONTRACT_STATUS",
        "PAYMENT_HISTORY",
        "BALANCE_QUERY",
        "NEXT_PAYMENT",
        "GENERAL_FINANCIAL_QUERY",
        "UNKNOWN",
    }


def test_parses_documented_example():
    # The exact shape the detector is expected to produce.
    result = IntentDetectionResult(**{"intent": "BALANCE_QUERY", "person": "John"})

    assert result.intent == AssistantIntent.BALANCE_QUERY
    assert result.person == "John"
    assert result.contract_reference is None


def test_reference_entity():
    result = IntentDetectionResult(intent="CONTRACT_STATUS", contract_reference="INV001")
    assert result.contract_reference == "INV001"
