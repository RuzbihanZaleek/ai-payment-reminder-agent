"""Rate limiting: backend behavior + dependency enforcement."""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.rate_limit import InMemoryRateLimitBackend, RateLimit
import app.core.rate_limit as rate_limit_module


# --- Backend ----------------------------------------------------------------

def test_backend_allows_up_to_limit_then_blocks():
    backend = InMemoryRateLimitBackend()

    # Fixed virtual clock so the window never advances.
    assert backend.allow("k", limit=2, window_seconds=60, now=100.0) is True
    assert backend.allow("k", limit=2, window_seconds=60, now=100.1) is True
    assert backend.allow("k", limit=2, window_seconds=60, now=100.2) is False


def test_backend_window_slides():
    backend = InMemoryRateLimitBackend()

    assert backend.allow("k", limit=1, window_seconds=60, now=0.0) is True
    assert backend.allow("k", limit=1, window_seconds=60, now=30.0) is False
    # After the window passes, the old hit is evicted.
    assert backend.allow("k", limit=1, window_seconds=60, now=61.0) is True


def test_backend_keys_are_independent():
    backend = InMemoryRateLimitBackend()

    assert backend.allow("a", limit=1, window_seconds=60, now=1.0) is True
    assert backend.allow("b", limit=1, window_seconds=60, now=1.0) is True


# --- Dependency -------------------------------------------------------------

def _app_with_limit(limit: int) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    dependency = RateLimit("test", lambda: limit)

    @app.get("/limited", dependencies=[Depends(dependency)])
    def _limited():
        return {"ok": True}

    return app


def test_dependency_enforces_limit(monkeypatch):
    # Enable limiting (disabled under APP_ENV=testing) with a fresh backend.
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(rate_limit_module, "_backend", InMemoryRateLimitBackend())

    client = TestClient(_app_with_limit(2))

    assert client.get("/limited").status_code == 200
    assert client.get("/limited").status_code == 200
    blocked = client.get("/limited")
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"


def test_dependency_is_disabled_under_testing(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "testing")
    monkeypatch.setattr(rate_limit_module, "_backend", InMemoryRateLimitBackend())

    client = TestClient(_app_with_limit(1))

    # Well beyond the limit, but testing disables enforcement.
    for _ in range(5):
        assert client.get("/limited").status_code == 200
