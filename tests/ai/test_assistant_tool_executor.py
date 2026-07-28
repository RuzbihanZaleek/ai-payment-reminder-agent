"""Intent-driven tool selection/execution."""

from app.ai.assistant.intent import AssistantIntent, IntentDetectionResult
from app.ai.assistant.tools import AssistantToolExecutor


class FakeContractTool:
    def __init__(self, active):
        self._active = active

    def get_active_contracts(self, user_id):
        return self._active

    def get_contract_summary(self, contract_id, user_id):
        return {"contract_id": contract_id, "remaining_amount": 900}


class FakePaymentTool:
    def get_payment_history(self, contract_id, user_id):
        return [{"payment_id": 1, "amount": 200}]


class FakeReceiptTool:
    def get_latest_receipts(self, contract_id, user_id):
        return [{"receipt_id": 1, "new_balance": 900}]


def _executor(active):
    return AssistantToolExecutor(FakeContractTool(active), FakePaymentTool(), FakeReceiptTool())


_ACTIVE = [
    {"contract_id": 1, "reference_code": "INV001", "name": "John Payment"},
    {"contract_id": 2, "reference_code": "INV002", "name": "Alice Payment"},
]


def test_balance_query_narrows_to_person():
    executor = _executor(_ACTIVE)
    intent = IntentDetectionResult(intent=AssistantIntent.BALANCE_QUERY, person="John")

    gathered = executor.gather(intent, user_id=7)

    # Only John's contract was summarized.
    assert len(gathered["context"]["contract_summaries"]) == 1
    assert gathered["context"]["contract_summaries"][0]["contract_id"] == 1
    assert "ContractTool.get_active_contracts" in gathered["tool_calls"]
    assert "ContractTool.get_contract_summary" in gathered["tool_calls"]


def test_contract_reference_takes_priority():
    executor = _executor(_ACTIVE)
    intent = IntentDetectionResult(
        intent=AssistantIntent.CONTRACT_STATUS, contract_reference="INV002"
    )

    gathered = executor.gather(intent, user_id=7)

    assert len(gathered["context"]["contract_summaries"]) == 1
    assert gathered["context"]["contract_summaries"][0]["contract_id"] == 2


def test_general_query_covers_all_contracts():
    executor = _executor(_ACTIVE)
    intent = IntentDetectionResult(intent=AssistantIntent.GENERAL_FINANCIAL_QUERY)

    gathered = executor.gather(intent, user_id=7)

    assert len(gathered["context"]["contract_summaries"]) == 2


def test_payment_history_includes_payments_and_receipts():
    executor = _executor(_ACTIVE)
    intent = IntentDetectionResult(intent=AssistantIntent.PAYMENT_HISTORY, person="John")

    gathered = executor.gather(intent, user_id=7)

    history = gathered["context"]["payment_history"]
    assert len(history) == 1
    assert history[0]["payments"] == [{"payment_id": 1, "amount": 200}]
    assert history[0]["latest_receipts"] == [{"receipt_id": 1, "new_balance": 900}]
    assert "PaymentTool.get_payment_history" in gathered["tool_calls"]
    assert "ReceiptTool.get_latest_receipts" in gathered["tool_calls"]


def test_unknown_intent_provides_only_active_contracts():
    executor = _executor(_ACTIVE)
    intent = IntentDetectionResult(intent=AssistantIntent.UNKNOWN)

    gathered = executor.gather(intent, user_id=7)

    assert "active_contracts" in gathered["context"]
    assert "contract_summaries" not in gathered["context"]
    assert "payment_history" not in gathered["context"]


def test_unmatched_person_yields_no_summaries():
    executor = _executor(_ACTIVE)
    intent = IntentDetectionResult(intent=AssistantIntent.BALANCE_QUERY, person="Nobody")

    gathered = executor.gather(intent, user_id=7)

    assert gathered["context"]["contract_summaries"] == []
