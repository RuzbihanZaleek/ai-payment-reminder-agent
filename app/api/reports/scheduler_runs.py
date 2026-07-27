from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.db.session import SessionLocal
from app.enums.scheduler_run_status import SchedulerRunStatus
from app.core.errors import NotFoundError, ErrorCode
from app.schemas.pagination import Page, PaginationParams
from app.repositories.filters import SchedulerRunFilter
from app.api.query_params import scheduler_run_filter_params
from app.container import create_scheduler_reporting_service
from app.services.scheduler_reporting_service import SchedulerReportingService
from app.api.deps import get_current_user


router = APIRouter(
    prefix="/reports/scheduler-runs",
    tags=["reports"],
    dependencies=[Depends(get_current_user)],
)


class SchedulerRunResponse(BaseModel):

    id: int
    run_type: str
    status: SchedulerRunStatus
    started_at: datetime
    completed_at: datetime | None
    total_contracts: int
    successful_count: int
    failed_count: int

    model_config = ConfigDict(from_attributes=True)


class SchedulerEventResponse(BaseModel):

    id: int
    scheduler_run_id: int
    contract_id: int
    status: str
    message: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SchedulerRunDetailResponse(BaseModel):

    run: SchedulerRunResponse
    events: list[SchedulerEventResponse]


def get_scheduler_reporting_service():

    db = SessionLocal()

    try:
        yield create_scheduler_reporting_service(db=db)
    finally:
        db.close()


@router.get("", response_model=Page[SchedulerRunResponse])
def list_scheduler_runs(
    pagination: PaginationParams = Depends(),
    run_filter: SchedulerRunFilter = Depends(scheduler_run_filter_params),
    service: SchedulerReportingService = Depends(get_scheduler_reporting_service),
):

    result = service.get_recent_runs(
        run_filter,
        pagination.page,
        pagination.page_size,
        pagination.order,
    )

    return Page.build(result, pagination.page, pagination.page_size)


@router.get("/{run_id}", response_model=SchedulerRunDetailResponse)
def get_scheduler_run(
    run_id: int,
    service: SchedulerReportingService = Depends(get_scheduler_reporting_service),
):

    details = service.get_run_details(run_id)

    if details is None:
        raise NotFoundError(
            "Scheduler run not found.",
            code=ErrorCode.SCHEDULER_RUN_NOT_FOUND,
        )

    return details