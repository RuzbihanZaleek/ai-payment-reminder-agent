"""API v1 aggregator.

Versioning is achieved purely by *re-mounting the existing feature routers*
under a single ``/api/v1`` prefix -- no endpoint code is duplicated. Infra and
external-contract endpoints (``/health``, ``/ready``, ``/webhook``, ``/``) stay
unversioned on purpose: they are operational probes and a fixed Meta webhook URL.
"""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.agent import router as agent_router
from app.api.approval import router as approval_router
from app.api.reports.contracts import router as reports_contracts_router
from app.api.reports.agent_runs import router as reports_agent_runs_router
from app.api.reports.scheduler_runs import router as reports_scheduler_runs_router
from app.api.dashboard import router as dashboard_router
from app.api.analytics import router as analytics_router
from app.api.admin.notifications import router as admin_notifications_router


API_V1_PREFIX = "/api/v1"

api_v1_router = APIRouter(prefix=API_V1_PREFIX)

# The same router objects the legacy mounts use -- one source of truth.
_FEATURE_ROUTERS = [
    auth_router,
    agent_router,
    approval_router,
    reports_contracts_router,
    reports_agent_runs_router,
    reports_scheduler_runs_router,
    dashboard_router,
    analytics_router,
    admin_notifications_router,
]

for _router in _FEATURE_ROUTERS:
    api_v1_router.include_router(_router)
