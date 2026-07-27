import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app.core.config import settings
from app.core.logger import get_logger, set_request_id
from app.core.errors import register_exception_handlers
from app.core.metrics import record_api_request
from app.scheduler import start_scheduler, shutdown_scheduler

from app.api.v1 import api_v1_router
from app.api.health import router as health_router
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Own the background scheduler's lifecycle with the app process.

    Started once on startup (skipped under testing / when disabled) and stopped
    cleanly on shutdown. A start failure never takes the API down.
    """

    app.state.scheduler = start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler(getattr(app.state, "scheduler", None))


def _unique_operation_id(route: APIRoute) -> str:
    """Path-derived operation ids so the legacy + /api/v1 mounts never collide."""

    tag = route.tags[0] if route.tags else "app"
    slug = route.path_format.replace("/", "_").replace("{", "").replace("}", "")
    return f"{tag}{slug}_{route.name}"


# Interactive docs can be disabled per environment (e.g. locked-down prod).
_docs_kwargs = (
    {}
    if settings.ENABLE_DOCS
    else {"docs_url": None, "redoc_url": None, "openapi_url": None}
)

app = FastAPI(
    title="AI Payment Reminder Agent",
    debug=settings.DEBUG,
    generate_unique_id_function=_unique_operation_id,
    lifespan=lifespan,
    **_docs_kwargs,
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
    allow_credentials=True,
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):

    request_id = request.headers.get("X-Request-ID") or uuid4().hex

    set_request_id(request_id)

    start = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        record_api_request(time.perf_counter() - start)

    response.headers["X-Request-ID"] = request_id

    return response


# Versioned API (preferred).
app.include_router(api_v1_router)

# Unversioned infrastructure / external-contract endpoints.
app.include_router(health_router)
app.include_router(whatsapp_router)

# Legacy unversioned mounts kept for backwards compatibility. Prefer /api/v1.
app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(approval_router)
app.include_router(reports_contracts_router)
app.include_router(reports_agent_runs_router)
app.include_router(reports_scheduler_runs_router)
app.include_router(dashboard_router)
app.include_router(analytics_router)


@app.get("/")
def root():
    return {
        "status": "running"
    }
