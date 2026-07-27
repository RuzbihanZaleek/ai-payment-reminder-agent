from uuid import uuid4

from fastapi import FastAPI, Request

from app.core.logger import get_logger, set_request_id
from app.api.auth import router as auth_router
from app.api.agent import router as agent_router
from app.api.whatsapp import router as whatsapp_router
from app.api.approval import router as approval_router
from app.api.reports.contracts import router as reports_contracts_router
from app.api.reports.agent_runs import router as reports_agent_runs_router
from app.api.reports.scheduler_runs import router as reports_scheduler_runs_router
from app.api.dashboard import router as dashboard_router
from app.api.analytics import router as analytics_router

logger = get_logger(__name__)

app = FastAPI(
    title="AI Payment Reminder Agent"
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):

    request_id = request.headers.get("X-Request-ID") or uuid4().hex

    set_request_id(request_id)

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response


app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(whatsapp_router)
app.include_router(approval_router)
app.include_router(reports_contracts_router)
app.include_router(reports_agent_runs_router)
app.include_router(reports_scheduler_runs_router)
app.include_router(dashboard_router)
app.include_router(analytics_router)


@app.get("/")
def health():
    return {
        "status": "running"
    }
