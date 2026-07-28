"""Intent schema + entity extraction shape."""

from app.ai.assistant.intent import AssistantIntent, IntentDetectionResult


def test_intent_defaults_to_unknown():
    result = IntentDetectionResult()
    assert result.intent == AssistantIntent.UNKNOWN
    assert result.person is None
    assert result.contract_reference is None


def test_core_and_insight_intents_present():
    values = {i.value for i in AssistantIntent}

    # Phase 11.1 core intents.
    assert {
        "CONTRACT_STATUS", "PAYMENT_HISTORY", "BALANCE_QUERY",
        "NEXT_PAYMENT", "GENERAL_FINANCIAL_QUERY", "UNKNOWN",
    } <= values

    # Phase 11.2 insight intents.
    assert {
        "FINANCIAL_SUMMARY", "CONTRACT_ANALYTICS", "PAYMENT_ANALYTICS",
        "TREND_ANALYSIS", "MONTHLY_REPORT", "TOP_DEBTORS", "TOP_PERFORMERS",
        "OVERDUE_CONTRACTS", "PAYMENT_BEHAVIOR", "PAYMENT_TRENDS",
        "ROI_ANALYSIS", "CASHFLOW_ANALYSIS", "REMINDER_ANALYTICS",
        "FINANCIAL_RECOMMENDATION",
    } <= values


def test_parses_documented_example():
    # The exact shape the detector is expected to produce.
    result = IntentDetectionResult(**{"intent": "BALANCE_QUERY", "person": "John"})

    assert result.intent == AssistantIntent.BALANCE_QUERY
    assert result.person == "John"
    assert result.contract_reference is None


def test_reference_entity():
    result = IntentDetectionResult(intent="CONTRACT_STATUS", contract_reference="INV001")
    assert result.contract_reference == "INV001"
