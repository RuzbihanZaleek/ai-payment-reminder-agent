from fastapi import APIRouter, Depends, HTTPException

from app.db.session import SessionLocal
from app.container import create_analytics_service
from app.schemas.analytics import AnalyticsOverview
from app.services.analytics_service import AnalyticsService


router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_analytics_service():

    db = SessionLocal()

    try:
        yield create_analytics_service(db=db)
    finally:
        db.close()


@router.get("/overview", response_model=AnalyticsOverview)
def get_overview(
    service: AnalyticsService = Depends(get_analytics_service),
):

    try:
        return service.get_overview()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to build analytics overview",
        ) from exc