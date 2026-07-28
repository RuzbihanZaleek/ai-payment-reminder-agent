from fastapi import APIRouter, Depends

from app.db.session import SessionLocal
from app.container import create_assistant_service
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from app.api.deps import get_current_user
from app.models.user import User


router = APIRouter(prefix="/assistant", tags=["assistant"])


def get_assistant_service():

    db = SessionLocal()

    try:
        yield create_assistant_service(db=db)
    finally:
        db.close()


@router.post("/chat", response_model=AssistantChatResponse)
def chat(
    request: AssistantChatRequest,
    current_user: User = Depends(get_current_user),
    service=Depends(get_assistant_service),
):
    # Thin router: the user_id comes from the JWT; the service does the work.
    result = service.chat(current_user.id, request.message)

    return AssistantChatResponse(**result)
