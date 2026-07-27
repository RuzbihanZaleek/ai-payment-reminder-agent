from fastapi import APIRouter, Depends

from app.db.session import SessionLocal
from app.container import create_dashboard_service
from app.schemas.dashboard import DashboardOverview
from app.services.dashboard_service import DashboardService
from app.api.deps import get_current_user
from app.models.user import User


router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
)


def get_dashboard_service():

    db = SessionLocal()

    try:
        yield create_dashboard_service(db=db)
    finally:
        db.close()


@router.get("/overview", response_model=DashboardOverview)
def get_overview(
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    # Any unexpected failure is standardized to a 500 envelope by the global
    # exception handler -- no per-router try/except needed.
    return service.get_overview(current_user.id)