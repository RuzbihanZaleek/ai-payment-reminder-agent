from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from app.db.session import SessionLocal
from app.enums.agent_run_status import AgentRunStatus
from app.enums.agent_event_status import AgentEventStatus
from app.container import create_agent_reporting_service
from app.services.agent_reporting_service import AgentReportingService
from app.api.deps import get_current_user


router = APIRouter(
    prefix="/reports/agent-runs",
    tags=["reports"],
    dependencies=[Depends(get_current_user)],
)


class AgentRunResponse(BaseModel):

    id: int
    contract_id: int
    message_id: str
    status: AgentRunStatus
    current_step: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AgentEventResponse(BaseModel):

    id: int
    agent_run_id: int
    node_name: str
    status: AgentEventStatus
    message: str | None
    duration_ms: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentRunDetailResponse(BaseModel):

    run: AgentRunResponse
    events: list[AgentEventResponse]


def get_agent_reporting_service():

    db = SessionLocal()

    try:
        yield create_agent_reporting_service(db=db)
    finally:
        db.close()


@router.get("", response_model=list[AgentRunResponse])
def list_agent_runs(
    service: AgentReportingService = Depends(get_agent_reporting_service),
):

    return service.get_recent_runs()


@router.get("/{run_id}", response_model=AgentRunDetailResponse)
def get_agent_run(
    run_id: int,
    service: AgentReportingService = Depends(get_agent_reporting_service),
):

    details = service.get_run_details(run_id)

    if details is None:
        raise HTTPException(status_code=404, detail="Agent run not found")

    return details