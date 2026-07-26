from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.container import create_agent_execution_service
from app.services.agent_execution_service import AgentExecutionService
from app.enums.reminder_decision import ReminderDecision


router = APIRouter(prefix="/agent", tags=["agent"])


class AgentMessageRequest(BaseModel):

    contract_id: int
    message_id: str
    message: str


class AgentMessageResponse(BaseModel):

    decision: ReminderDecision
    generated_message: str | None
    requires_approval: bool
    notification_sent: bool


def get_agent_execution_service() -> AgentExecutionService:

    return create_agent_execution_service()


@router.post("/messages", response_model=AgentMessageResponse)
def create_agent_message(
    request: AgentMessageRequest,
    service: AgentExecutionService = Depends(get_agent_execution_service),
) -> AgentMessageResponse:

    try:
        state = service.execute(
            contract_id=request.contract_id,
            message_id=request.message_id,
            message=request.message,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Agent execution failed",
        ) from exc

    return AgentMessageResponse(
        decision=state.decision,
        generated_message=state.generated_message,
        requires_approval=state.requires_approval,
        notification_sent=state.notification_sent,
    )
