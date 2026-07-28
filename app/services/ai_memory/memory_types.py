from enum import Enum


class FinancialMemoryType(str, Enum):
    """Categories of long-term financial memory kept about a user."""

    PREFERENCE = "PREFERENCE"           # e.g. "prefers weekly reports"
    FINANCIAL_PATTERN = "FINANCIAL_PATTERN"  # e.g. "customers usually pay late"
    IMPORTANT_CONTEXT = "IMPORTANT_CONTEXT"
    RISK_SIGNAL = "RISK_SIGNAL"         # detected by proactive analysis
    USER_GOAL = "USER_GOAL"            # e.g. "wants monthly summaries"
