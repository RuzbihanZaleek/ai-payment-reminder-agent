from fastapi import APIRouter, Depends, HTTPException

from app.db.session import SessionLocal
from app.container import create_analytics_service
from app.schemas.analytics import AnalyticsOverview
from app.services.analytics_service import AnalyticsService
from app.api.deps import get_current_user
from app.models.user import User


router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
)


def get_analytics_service():

    db = SessionLocal()

    try:
        yield create_analytics_service(db=db)
    finally:
        db.close()


@router.get("/overview", response_model=AnalyticsOverview)
def get_overview(
    current_user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
):

    try:
        return service.get_overview(current_user.id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to build analytics overview",
        ) from exc