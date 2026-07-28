"""Assistant prompts.

Re-exports the shared system prompt and adds the intent-detection instruction.
"""

from app.ai.prompts import ASSISTANT_SYSTEM_PROMPT


INTENT_DETECTION_PROMPT = (
    "You classify a user's financial question into one intent and extract any "
    "named entities.\n"
    "\n"
    "Intents:\n"
    "- CONTRACT_STATUS: status/overview of a specific contract.\n"
    "- PAYMENT_HISTORY: past payments for a contract/person.\n"
    "- BALANCE_QUERY: how much is owed / remaining / still to pay.\n"
    "- NEXT_PAYMENT: the next/daily payment amount or schedule.\n"
    "- GENERAL_FINANCIAL_QUERY: a broad question across contracts.\n"
    "- FINANCIAL_SUMMARY: overall portfolio health / how am I doing.\n"
    "- CONTRACT_SUMMARY / CONTRACT_ANALYTICS: contract portfolio breakdown.\n"
    "- PAYMENT_SUMMARY / PAYMENT_ANALYTICS / PAYMENT_BEHAVIOR: payment stats/behaviour.\n"
    "- TREND_ANALYSIS / PAYMENT_TRENDS / MONTHLY_REPORT: trends over time.\n"
    "- TOP_DEBTORS: who owes the most.\n"
    "- TOP_PERFORMERS: best-paying contracts/people.\n"
    "- OVERDUE_CONTRACTS: contracts behind schedule.\n"
    "- ROI_ANALYSIS: return / collection performance.\n"
    "- CASHFLOW_ANALYSIS: expected income / cashflow.\n"
    "- REMINDER_ANALYTICS: reminder delivery statistics.\n"
    "- FINANCIAL_RECOMMENDATION: advice on the portfolio.\n"
    "- UNKNOWN: anything not about the user's finances.\n"
    "\n"
    "Extract 'person' if a contract holder's name is mentioned, and "
    "'contract_reference' if a reference code (e.g. INV001) is mentioned. "
    "Return null for entities that are not present."
)


__all__ = ["ASSISTANT_SYSTEM_PROMPT", "INTENT_DETECTION_PROMPT"]
