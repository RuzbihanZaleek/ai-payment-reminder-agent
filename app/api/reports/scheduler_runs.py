from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from app.db.session import SessionLocal
from app.enums.scheduler_run_status import SchedulerRunStatus
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


@router.get("", response_model=list[SchedulerRunResponse])
def list_scheduler_runs(
    service: SchedulerReportingService = Depends(get_scheduler_reporting_service),
):

    return service.get_recent_runs()


@router.get("/{run_id}", response_model=SchedulerRunDetailResponse)
def get_scheduler_run(
    run_id: int,
    service: SchedulerReportingService = Depends(get_scheduler_reporting_service),
):

    details = service.get_run_details(run_id)

    if details is None:
        raise HTTPException(status_code=404, detail="Scheduler run not found")

    return details