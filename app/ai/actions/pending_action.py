from enum import Enum


class ActionType(str, Enum):
    """Write actions the AI agent can propose (V1 -- deliberately minimal)."""

    CREATE_CONTRACT = "CREATE_CONTRACT"
    APPROVE_PAYMENT = "APPROVE_PAYMENT"
    REJECT_PAYMENT = "REJECT_PAYMENT"
    SEND_REMINDERS = "SEND_REMINDERS"


class PendingActionStatus(str, Enum):
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
