from enum import Enum

from pydantic import BaseModel, Field


class AssistantIntent(str, Enum):
    # Phase 11.1 (question answering).
    CONTRACT_STATUS = "CONTRACT_STATUS"
    PAYMENT_HISTORY = "PAYMENT_HISTORY"
    BALANCE_QUERY = "BALANCE_QUERY"
    NEXT_PAYMENT = "NEXT_PAYMENT"
    GENERAL_FINANCIAL_QUERY = "GENERAL_FINANCIAL_QUERY"
    UNKNOWN = "UNKNOWN"

    # Phase 11.2 (insights & recommendations).
    FINANCIAL_SUMMARY = "FINANCIAL_SUMMARY"
    CONTRACT_SUMMARY = "CONTRACT_SUMMARY"
    PAYMENT_SUMMARY = "PAYMENT_SUMMARY"
    CONTRACT_ANALYTICS = "CONTRACT_ANALYTICS"
    PAYMENT_ANALYTICS = "PAYMENT_ANALYTICS"
    TREND_ANALYSIS = "TREND_ANALYSIS"
    MONTHLY_REPORT = "MONTHLY_REPORT"
    TOP_DEBTORS = "TOP_DEBTORS"
    TOP_PERFORMERS = "TOP_PERFORMERS"
    OVERDUE_CONTRACTS = "OVERDUE_CONTRACTS"
    PAYMENT_BEHAVIOR = "PAYMENT_BEHAVIOR"
    PAYMENT_TRENDS = "PAYMENT_TRENDS"
    ROI_ANALYSIS = "ROI_ANALYSIS"
    CASHFLOW_ANALYSIS = "CASHFLOW_ANALYSIS"
    REMINDER_ANALYTICS = "REMINDER_ANALYTICS"
    FINANCIAL_RECOMMENDATION = "FINANCIAL_RECOMMENDATION"


class IntentDetectionResult(BaseModel):
    """The classified intent plus any entities extracted from the message."""

    intent: AssistantIntent = AssistantIntent.UNKNOWN

    # Optional entities the LLM may extract to focus the answer.
    person: str | None = Field(
        default=None,
        description="A contract holder / person named in the question, if any.",
    )
    contract_reference: str | None = Field(
        default=None,
        description="A contract reference code named in the question, if any.",
    )
