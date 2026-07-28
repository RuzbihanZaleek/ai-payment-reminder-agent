"""Tool selection + execution for the assistant.

Deterministic, code-driven orchestration: given a detected intent (and any
entities), it selects which read-only tools to run and assembles a structured
``context`` for the LLM to answer from. The LLM never chooses data or tools --
that is what keeps it from hallucinating figures.

Phase 11.1 intents answer from per-contract data; Phase 11.2 intents answer from
the insight tools (portfolio/contract/payment/reminder analytics + grounded
recommendations). The insight tools are optional so the executor still works if
they are not wired (e.g. focused unit tests).
"""

from app.ai.assistant.intent import AssistantIntent, IntentDetectionResult
from app.ai.tools import ContractTool, PaymentTool, ReceiptTool


# --- Phase 11.1 (per-contract) intents --------------------------------------
_SUMMARY_INTENTS = {
    AssistantIntent.CONTRACT_STATUS,
    AssistantIntent.BALANCE_QUERY,
    AssistantIntent.NEXT_PAYMENT,
    AssistantIntent.GENERAL_FINANCIAL_QUERY,
}

# --- Phase 11.2 (insight) intent groups -------------------------------------
_FINANCIAL_INTENTS = {
    AssistantIntent.FINANCIAL_SUMMARY,
    AssistantIntent.ROI_ANALYSIS,
    AssistantIntent.CASHFLOW_ANALYSIS,
}
_CONTRACT_INSIGHT_INTENTS = {
    AssistantIntent.CONTRACT_SUMMARY,
    AssistantIntent.CONTRACT_ANALYTICS,
    AssistantIntent.OVERDUE_CONTRACTS,
}
_PAYMENT_INSIGHT_INTENTS = {
    AssistantIntent.PAYMENT_SUMMARY,
    AssistantIntent.PAYMENT_ANALYTICS,
    AssistantIntent.PAYMENT_BEHAVIOR,
}
_TREND_INTENTS = {
    AssistantIntent.PAYMENT_TRENDS,
    AssistantIntent.TREND_ANALYSIS,
}
_PAYER_INTENTS = {
    AssistantIntent.TOP_DEBTORS,
    AssistantIntent.TOP_PERFORMERS,
}


class AssistantToolExecutor:

    def __init__(
        self,
        contract_tool: ContractTool,
        payment_tool: PaymentTool,
        receipt_tool: ReceiptTool,
        financial_insight_tool=None,
        contract_insight_tool=None,
        payment_insight_tool=None,
        scheduler_insight_tool=None,
        recommendation_tool=None,
        approval_tool=None,
    ):
        self.contract_tool = contract_tool
        self.payment_tool = payment_tool
        self.receipt_tool = receipt_tool
        self.financial_insight_tool = financial_insight_tool
        self.contract_insight_tool = contract_insight_tool
        self.payment_insight_tool = payment_insight_tool
        self.scheduler_insight_tool = scheduler_insight_tool
        self.recommendation_tool = recommendation_tool
        self.approval_tool = approval_tool

    def gather(self, intent_result: IntentDetectionResult, user_id: int) -> dict:
        """Return {"context": {...}, "tool_calls": [...]} for the given intent."""

        intent = intent_result.intent
        context: dict = {}
        tool_calls: list[str] = []

        # --- Phase 11.1 + SHOW_CONTRACTS: per-contract answering ------------
        if intent in _SUMMARY_INTENTS or intent in (
            AssistantIntent.PAYMENT_HISTORY,
            AssistantIntent.SHOW_CONTRACTS,
            AssistantIntent.UNKNOWN,
        ):
            return self._gather_contract_level(intent_result, user_id)

        # --- Phase 11.4 read actions ----------------------------------------
        if intent == AssistantIntent.SHOW_PAYMENTS:
            self._add_payments(context, tool_calls, user_id)
            return {"context": context, "tool_calls": tool_calls}

        if intent == AssistantIntent.SHOW_PENDING_APPROVALS:
            if self.approval_tool is not None:
                context["pending_approvals"] = self.approval_tool.get_pending_approvals(user_id)
                tool_calls.append("ApprovalTool.get_pending_approvals")
            return {"context": context, "tool_calls": tool_calls}

        # --- Phase 11.2: insight intents ------------------------------------
        if intent in _FINANCIAL_INTENTS:
            self._add_financial(context, tool_calls, user_id)

        elif intent in _CONTRACT_INSIGHT_INTENTS:
            self._add_contracts(context, tool_calls, user_id)

        elif intent in _PAYMENT_INSIGHT_INTENTS:
            self._add_payments(context, tool_calls, user_id)

        elif intent in _TREND_INTENTS:
            self._add_payment_trends(context, tool_calls, user_id)

        elif intent in _PAYER_INTENTS:
            self._add_contracts(context, tool_calls, user_id)
            self._add_payers(context, tool_calls, user_id)

        elif intent == AssistantIntent.MONTHLY_REPORT:
            self._add_financial(context, tool_calls, user_id)
            self._add_payment_trends(context, tool_calls, user_id)

        elif intent == AssistantIntent.REMINDER_ANALYTICS:
            self._add_reminders(context, tool_calls, user_id)

        elif intent == AssistantIntent.FINANCIAL_RECOMMENDATION:
            self._add_financial(context, tool_calls, user_id)
            self._add_contracts(context, tool_calls, user_id)
            self._add_payments(context, tool_calls, user_id)
            self._add_recommendations(context, tool_calls, user_id)

        return {"context": context, "tool_calls": tool_calls}

    # --- Phase 11.1 handler -------------------------------------------------

    def _gather_contract_level(self, intent_result: IntentDetectionResult, user_id: int) -> dict:
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

        return {"context": context, "tool_calls": tool_calls}

    # --- Phase 11.2 helpers (each uses exactly one insight tool) ------------

    def _add_financial(self, context, tool_calls, user_id):
        if self.financial_insight_tool is None:
            return
        context["financial"] = self.financial_insight_tool.get_financial_overview(user_id)
        tool_calls.append("FinancialInsightTool.get_financial_overview")

    def _add_contracts(self, context, tool_calls, user_id):
        if self.contract_insight_tool is None:
            return
        context["contracts"] = self.contract_insight_tool.get_contract_overview(user_id)
        tool_calls.append("ContractInsightTool.get_contract_overview")

    def _add_payments(self, context, tool_calls, user_id):
        if self.payment_insight_tool is None:
            return
        context["payments"] = self.payment_insight_tool.get_payment_overview(user_id)
        tool_calls.append("PaymentInsightTool.get_payment_overview")

    def _add_payment_trends(self, context, tool_calls, user_id):
        if self.payment_insight_tool is None:
            return
        context["payment_trends"] = self.payment_insight_tool.get_payment_trends(user_id)
        tool_calls.append("PaymentInsightTool.get_payment_trends")

    def _add_payers(self, context, tool_calls, user_id):
        if self.payment_insight_tool is None:
            return
        context["payers"] = self.payment_insight_tool.get_payers(user_id)
        tool_calls.append("PaymentInsightTool.get_payers")

    def _add_reminders(self, context, tool_calls, user_id):
        if self.scheduler_insight_tool is None:
            return
        context["reminders"] = self.scheduler_insight_tool.get_reminder_overview(user_id)
        tool_calls.append("SchedulerInsightTool.get_reminder_overview")

    def _add_recommendations(self, context, tool_calls, user_id):
        if self.recommendation_tool is None:
            return
        context["recommendations"] = self.recommendation_tool.get_recommendations(
            user_id
        )["recommendations"]
        tool_calls.append("RecommendationTool.get_recommendations")

    @staticmethod
    def _resolve_targets(active, intent_result):
        reference = (intent_result.contract_reference or "").strip().lower()
        person = (intent_result.person or "").strip().lower()

        if reference:
            return [c for c in active if reference in (c["reference_code"] or "").lower()]

        if person:
            return [c for c in active if person in (c["name"] or "").lower()]

        return active
