"""Assistant prompts.

Re-exports the shared system prompt and adds the intent-detection instruction.
"""

from app.ai.prompts import ASSISTANT_SYSTEM_PROMPT


INTENT_DETECTION_PROMPT = (
    "You classify a user's financial question into one intent and extract any "
    "named entities.\n"
    "\n"
    "Intents:\n"
    "- CONTRACT_STATUS: status/overview of a contract.\n"
    "- PAYMENT_HISTORY: past payments for a contract/person.\n"
    "- BALANCE_QUERY: how much is owed / remaining / still to pay.\n"
    "- NEXT_PAYMENT: the next/daily payment amount or schedule.\n"
    "- GENERAL_FINANCIAL_QUERY: a broad financial question across contracts.\n"
    "- UNKNOWN: anything not about the user's contracts/payments.\n"
    "\n"
    "Extract 'person' if a contract holder's name is mentioned, and "
    "'contract_reference' if a reference code (e.g. INV001) is mentioned. "
    "Return null for entities that are not present."
)


__all__ = ["ASSISTANT_SYSTEM_PROMPT", "INTENT_DETECTION_PROMPT"]
