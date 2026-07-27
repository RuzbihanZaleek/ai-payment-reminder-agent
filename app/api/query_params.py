"""FastAPI dependencies that translate query parameters into neutral filters.

Routers depend on these so they never construct or validate filters inline --
they receive a ready-made value object and forward it to the service/repository.
"""

from datetime import date
from decimal import Decimal

from fastapi import Query

from app.enums.payment_status import PaymentStatus
from app.enums.approval_status import ApprovalStatus
from app.enums.agent_run_status import AgentRunStatus
from app.enums.scheduler_run_status import SchedulerRunStatus
from app.repositories.filters import (
    PaymentFilter,
    AgentRunFilter,
    SchedulerRunFilter,
)


def payment_filter_params(
    status: PaymentStatus | None = Query(default=None),
    approval_status: ApprovalStatus | None = Query(default=None),
    date_from: date | None = Query(default=None, description="Inclusive lower bound on payment_date"),
    date_to: date | None = Query(default=None, description="Inclusive upper bound on payment_date"),
    min_amount: Decimal | None = Query(default=None, ge=0),
    max_amount: Decimal | None = Query(default=None, ge=0),
) -> PaymentFilter:
    return PaymentFilter(
        status=status,
        approval_status=approval_status,
        date_from=date_from,
        date_to=date_to,
        min_amount=min_amount,
        max_amount=max_amount,
    )


def agent_run_filter_params(
    status: AgentRunStatus | None = Query(default=None),
    date_from: date | None = Query(default=None, description="Inclusive lower bound on created_at"),
    date_to: date | None = Query(default=None, description="Inclusive upper bound on created_at"),
) -> AgentRunFilter:
    return AgentRunFilter(status=status, date_from=date_from, date_to=date_to)


def scheduler_run_filter_params(
    status: SchedulerRunStatus | None = Query(default=None),
) -> SchedulerRunFilter:
    return SchedulerRunFilter(status=status)


def approval_status_param(
    status: ApprovalStatus = Query(
        default=ApprovalStatus.PENDING,
        description="Approval status to list (pending/approved/rejected)",
    ),
) -> ApprovalStatus:
    return status
