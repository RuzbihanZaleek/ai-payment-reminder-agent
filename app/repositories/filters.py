"""Neutral filter value-objects consumed by repositories.

These are plain dataclasses (no FastAPI/pydantic coupling) so services and
repositories can accept a typed filter without depending on the API layer. The
API builds them from query parameters; every field is optional and ``None``
means "don't filter on this".
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.enums.payment_status import PaymentStatus
from app.enums.approval_status import ApprovalStatus
from app.enums.agent_run_status import AgentRunStatus
from app.enums.scheduler_run_status import SchedulerRunStatus
from app.models.contract import ContractStatus


@dataclass
class PaymentFilter:
    status: PaymentStatus | None = None
    approval_status: ApprovalStatus | None = None
    date_from: date | None = None
    date_to: date | None = None
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None


@dataclass
class AgentRunFilter:
    status: AgentRunStatus | None = None
    date_from: date | None = None
    date_to: date | None = None


@dataclass
class SchedulerRunFilter:
    status: SchedulerRunStatus | None = None


@dataclass
class ContractFilter:
    status: ContractStatus | None = None
