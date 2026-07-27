from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.db.session import SessionLocal
from app.enums.agent_run_status import AgentRunStatus
from app.enums.agent_event_status import AgentEventStatus
from app.container import create_agent_reporting_service
from app.services.agent_reporting_service import AgentReportingService
from app.core.errors import NotFoundError, ErrorCode
from app.schemas.pagination import Page, PaginationParams
from app.repositories.filters import AgentRunFilter
from app.api.query_params import agent_run_filter_params
from app.api.deps import get_current_user
from app.models.user import User


router = APIRouter(
    prefix="/reports/agent-runs",
    tags=["reports"],
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


@router.get("", response_model=Page[AgentRunResponse])
def list_agent_runs(
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends(),
    run_filter: AgentRunFilter = Depends(agent_run_filter_params),
    service: AgentReportingService = Depends(get_agent_reporting_service),
):

    result = service.get_recent_runs(
        current_user.id,
        run_filter,
        pagination.page,
        pagination.page_size,
        pagination.order,
    )

    return Page.build(result, pagination.page, pagination.page_size)


@router.get("/{run_id}", response_model=AgentRunDetailResponse)
def get_agent_run(
    run_id: int,
    current_user: User = Depends(get_current_user),
    service: AgentReportingService = Depends(get_agent_reporting_service),
):

    details = service.get_run_details(run_id, current_user.id)

    if details is None:
        raise NotFoundError("Agent run not found.", code=ErrorCode.AGENT_RUN_NOT_FOUND)

    return details