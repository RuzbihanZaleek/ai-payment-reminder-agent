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

    # Phase 11.4 (agent actions -- writes require explicit confirmation).
    CREATE_CONTRACT = "CREATE_CONTRACT"
    UPDATE_CONTRACT = "UPDATE_CONTRACT"      # detected but not supported in V1
    DELETE_CONTRACT = "DELETE_CONTRACT"      # detected but not supported in V1
    APPROVE_PAYMENT = "APPROVE_PAYMENT"
    REJECT_PAYMENT = "REJECT_PAYMENT"
    SEND_REMINDERS = "SEND_REMINDERS"
    SHOW_PENDING_APPROVALS = "SHOW_PENDING_APPROVALS"
    SHOW_CONTRACTS = "SHOW_CONTRACTS"
    SHOW_PAYMENTS = "SHOW_PAYMENTS"
    CONFIRM_ACTION = "CONFIRM_ACTION"
    CANCEL_ACTION = "CANCEL_ACTION"


class IntentDetectionResult(BaseModel):
    """The classified intent plus any entities extracted from the message."""

    intent: AssistantIntent = AssistantIntent.UNKNOWN

    # Optional entities the LLM may extract to focus the answer / action.
    person: str | None = Field(
        default=None,
        description="A contract holder / customer name named in the message, if any.",
    )
    contract_reference: str | None = Field(
        default=None,
        description="A contract reference code named in the message, if any.",
    )
    amount: float | None = Field(
        default=None,
        description="A total contract amount named in the message, if any.",
    )
    daily_amount: float | None = Field(
        default=None,
        description="A daily payment amount named in the message, if any.",
    )
    payment_id: int | None = Field(
        default=None,
        description="A specific payment id named in the message, if any.",
    )
    phone: str | None = Field(
        default=None,
        description="A customer's WhatsApp phone number named in the conversation, if any.",
    )
