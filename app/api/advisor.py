from fastapi import APIRouter, Depends

from app.db.session import SessionLocal
from app.container import create_recommendation_service
from app.schemas.advisor import AdvisorResponse
from app.api.deps import get_current_user
from app.models.user import User


router = APIRouter(prefix="/advisor", tags=["advisor"])


def get_recommendation_service():

    db = SessionLocal()

    try:
        yield create_recommendation_service(db=db)
    finally:
        db.close()


@router.post("/analyze", response_model=AdvisorResponse)
def analyze(
    current_user: User = Depends(get_current_user),
    service=Depends(get_recommendation_service),
):
    # Thin router: user_id from the JWT; all analysis lives in the service.
    result = service.generate_personalized_recommendations(current_user.id)

    return AdvisorResponse(
        summary=result["summary"],
        risks=result["risks"],
        recommendations=result["suggestions"],
    )
