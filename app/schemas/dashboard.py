from decimal import Decimal

from pydantic import BaseModel


class ContractDashboard(BaseModel):

    total_contracts: int
    active_contracts: int
    completed_contracts: int
    total_remaining_amount: Decimal


class PaymentDashboard(BaseModel):

    payment_transaction_count: int
    total_amount_received: Decimal
    pending_review_count: int
    pending_review_amount: Decimal


class AgentDashboard(BaseModel):

    total_agent_runs: int
    completed_runs: int
    failed_runs: int


class SchedulerDashboard(BaseModel):

    total_scheduler_runs: int
    failed_scheduler_runs: int
    total_reminders_sent: int
    total_reminders_failed: int


class DashboardOverview(BaseModel):

    contracts: ContractDashboard
    payments: PaymentDashboard
    agents: AgentDashboard
    scheduler: SchedulerDashboard