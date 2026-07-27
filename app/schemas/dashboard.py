from decimal import Decimal

from pydantic import BaseModel


class ContractDashboard(BaseModel):

    total_contracts: int
    active_contracts: int
    completed_contracts: int
    total_remaining_amount: Decimal


class PaymentDashboard(BaseModel):

    total_payments_received: int
    pending_approval_count: int


class AgentDashboard(BaseModel):

    total_agent_runs: int
    completed_runs: int
    failed_runs: int


class SchedulerDashboard(BaseModel):

    total_scheduler_runs: int
    successful_runs: int
    failed_runs: int


class DashboardOverview(BaseModel):

    contracts: ContractDashboard
    payments: PaymentDashboard
    agents: AgentDashboard
    scheduler: SchedulerDashboard