from fastapi import APIRouter, Depends, HTTPException

from app.db.session import SessionLocal
from app.container import create_dashboard_service
from app.schemas.dashboard import DashboardOverview
from app.services.dashboard_service import DashboardService
from app.api.deps import get_current_user


router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_current_user)],
)


def get_dashboard_service():

    db = SessionLocal()

    try:
        yield create_dashboard_service(db=db)
    finally:
        db.close()


@router.get("/overview", response_model=DashboardOverview)
def get_overview(
    service: DashboardService = Depends(get_dashboard_service),
):

    try:
        return service.get_overview()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to build dashboard overview",
        ) from exc