"""Tool selection + execution for the assistant.

Deterministic, code-driven orchestration: given a detected intent (and any
entities), it selects which read-only tools to run, resolves the target
contract(s) from the user's own data, and assembles a structured ``context`` for
the LLM to answer from. The LLM never chooses data -- it only phrases the answer
from what these tools return, which is what keeps it from hallucinating figures.
"""

from app.ai.assistant.intent import AssistantIntent, IntentDetectionResult
from app.ai.tools import ContractTool, PaymentTool, ReceiptTool


# Intents that are answered from contract summaries (status/balance/next payment).
_SUMMARY_INTENTS = {
    AssistantIntent.CONTRACT_STATUS,
    AssistantIntent.BALANCE_QUERY,
    AssistantIntent.NEXT_PAYMENT,
    AssistantIntent.GENERAL_FINANCIAL_QUERY,
}


class AssistantToolExecutor:

    def __init__(
        self,
        contract_tool: ContractTool,
        payment_tool: PaymentTool,
        receipt_tool: ReceiptTool,
    ):
        self.contract_tool = contract_tool
        self.payment_tool = payment_tool
        self.receipt_tool = receipt_tool

    def gather(self, intent_result: IntentDetectionResult, user_id: int) -> dict:
        """Return {"context": {...}, "tool_calls": [...]} for the given intent."""

        tool_calls: list[str] = []

        active = self.contract_tool.get_active_contracts(user_id)
        tool_calls.append("ContractTool.get_active_contracts")

        targets = self._resolve_targets(active, intent_result)

        context: dict = {"active_contracts": active}
        intent = intent_result.intent

        if intent in _SUMMARY_INTENTS:
            summaries = []
            for contract in targets:
                summary = self.contract_tool.get_contract_summary(
                    contract["contract_id"], user_id
                )
                tool_calls.append("ContractTool.get_contract_summary")
                if summary is not None:
                    summaries.append(summary)
            context["contract_summaries"] = summaries

        elif intent == AssistantIntent.PAYMENT_HISTORY:
            histories = []
            for contract in targets:
                cid = contract["contract_id"]
                payments = self.payment_tool.get_payment_history(cid, user_id)
                receipts = self.receipt_tool.get_latest_receipts(cid, user_id)
                tool_calls.append("PaymentTool.get_payment_history")
                tool_calls.append("ReceiptTool.get_latest_receipts")
                histories.append(
                    {
                        "contract_id": cid,
                        "reference_code": contract["reference_code"],
                        "payments": payments,
                        "latest_receipts": receipts,
                    }
                )
            context["payment_history"] = histories

        # UNKNOWN (and anything else): only the active-contract list is provided,
        # so the LLM can offer to help or ask for clarification -- never invent.

        return {"context": context, "tool_calls": tool_calls}

    @staticmethod
    def _resolve_targets(
        active: list[dict],
        intent_result: IntentDetectionResult,
    ) -> list[dict]:
        """Narrow the active contracts to those the question is about."""

        reference = (intent_result.contract_reference or "").strip().lower()
        person = (intent_result.person or "").strip().lower()

        if reference:
            return [
                c for c in active if reference in (c["reference_code"] or "").lower()
            ]

        if person:
            return [c for c in active if person in (c["name"] or "").lower()]

        return active
