"""API versioning: /api/v1 routes work alongside the legacy unversioned ones."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.auth import get_auth_service


client = TestClient(app)


class FakeAuthService:
    def register(self, email, password):
        return SimpleNamespace(id=1, email=email, created_at="2026-07-28T00:00:00Z")

    def authenticate(self, email, password):
        return None  # force a deterministic 401 without touching a DB


@pytest.fixture(autouse=True)
def _override():
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    yield
    app.dependency_overrides.clear()


def test_v1_login_route_exists():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "a@b.com", "password": "password123"},
    )
    # Route resolves and runs the handler (invalid creds -> standardized 401).
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_legacy_login_route_still_works():
    response = client.post(
        "/auth/login",
        json={"email": "a@b.com", "password": "password123"},
    )
    assert response.status_code == 401


def test_v1_and_legacy_share_behavior():
    v1 = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "password123"})
    legacy = client.post("/auth/login", json={"email": "a@b.com", "password": "password123"})
    assert v1.status_code == legacy.status_code


def test_openapi_generates_without_operation_id_collisions():
    # Dual-mounting must not break schema generation (unique operation ids).
    schema = app.openapi()
    assert "/api/v1/auth/login" in schema["paths"]
    assert "/auth/login" in schema["paths"]
