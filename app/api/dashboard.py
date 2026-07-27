from fastapi import APIRouter, Depends

from app.db.session import SessionLocal
from app.container import create_dashboard_service, create_system_reporting_service
from app.schemas.dashboard import DashboardOverview, SystemDashboard
from app.services.dashboard_service import DashboardService
from app.services.system_reporting_service import SystemReportingService
from app.api.deps import get_current_user, require_admin
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


def get_system_reporting_service():

    db = SessionLocal()

    try:
        yield create_system_reporting_service(db=db)
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


@router.get("/system", response_model=SystemDashboard)
def get_system(
    _admin: User = Depends(require_admin),
    service: SystemReportingService = Depends(get_system_reporting_service),
):
    # Operational health is admin-only.
    return service.get_system_stats()