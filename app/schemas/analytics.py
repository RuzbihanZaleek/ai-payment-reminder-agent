from decimal import Decimal

from pydantic import BaseModel


class ContractAnalytics(BaseModel):

    total_contract_value: Decimal
    total_collected_amount: Decimal
    total_outstanding_amount: Decimal
    collection_rate: float


class PaymentAnalytics(BaseModel):

    total_amount_received: Decimal
    payment_transaction_count: int
    average_payment_amount: Decimal
    pending_review_amount: Decimal


class ReminderAnalytics(BaseModel):

    total_reminders_logged: int
    total_reminders_sent: int
    total_reminders_failed: int
    delivery_rate: float


class AgentAnalytics(BaseModel):

    total_agent_runs: int
    completed_runs: int
    failed_runs: int
    success_rate: float


class AnalyticsOverview(BaseModel):

    contracts: ContractAnalytics
    payments: PaymentAnalytics
    reminders: ReminderAnalytics
    agents: AgentAnalytics