from enum import Enum

from pydantic import BaseModel, Field


class AssistantIntent(str, Enum):
    CONTRACT_STATUS = "CONTRACT_STATUS"
    PAYMENT_HISTORY = "PAYMENT_HISTORY"
    BALANCE_QUERY = "BALANCE_QUERY"
    NEXT_PAYMENT = "NEXT_PAYMENT"
    GENERAL_FINANCIAL_QUERY = "GENERAL_FINANCIAL_QUERY"
    UNKNOWN = "UNKNOWN"


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
