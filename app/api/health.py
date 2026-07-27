"""Liveness and readiness endpoints.

- ``GET /health`` is a *liveness* probe: it answers "is the process up?" and does
  no I/O, so it never fails because of a downstream dependency.
- ``GET /ready`` is a *readiness* probe: it verifies the app can actually serve
  traffic -- database reachable and the required configuration present. It
  returns 503 when any check fails so orchestrators keep traffic away until the
  instance is truly ready.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal
from app.core.logger import get_logger
from app.core.metrics import metrics
from app.services.alert_service import default_alert_service


logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness: the process is running and can serve HTTP."""

    return {"status": "ok"}


@router.get("/metrics")
def prometheus_metrics() -> PlainTextResponse:
    """Prometheus-compatible metrics exposition (process-local counters)."""

    return PlainTextResponse(
        content=metrics.render(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


def _check_database() -> bool:
    """Lightweight connectivity check -- a single ``SELECT 1``."""

    db = SessionLocal()

    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.warning("readiness_database_check_failed")
        default_alert_service.notify_error("Database readiness check failed")
        return False
    finally:
        db.close()


def _check_jwt_config() -> bool:
    return bool(settings.JWT_SECRET_KEY) and bool(settings.JWT_ALGORITHM)


def _check_openai_config() -> bool:
    return bool(settings.OPENAI_API_KEY) and bool(settings.OPENAI_MODEL)


def _check_whatsapp_config() -> bool:
    # A verify token is the minimum needed to accept inbound webhooks.
    return bool(settings.WHATSAPP_VERIFY_TOKEN)


@router.get("/ready")
def ready() -> JSONResponse:
    """Readiness: dependencies reachable and required config loaded."""

    checks = {
        "database": _check_database(),
        "jwt_config": _check_jwt_config(),
        "openai_config": _check_openai_config(),
        "whatsapp_config": _check_whatsapp_config(),
    }

    ready = all(checks.values())
    status_code = 200 if ready else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if ready else "not_ready",
            "checks": checks,
        },
    )