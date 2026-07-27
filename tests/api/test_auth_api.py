from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.auth import get_auth_service
from app.services.auth_service import EmailAlreadyRegisteredError


client = TestClient(app)

DT = datetime(2026, 7, 27, 12, 0, 0)


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.clear()


class FakeAuthService:

    def __init__(self, exists=False, authenticated_user=None):
        self.exists = exists
        self.authenticated_user = authenticated_user

    def register(self, email, password):
        if self.exists:
            raise EmailAlreadyRegisteredError(email)
        return SimpleNamespace(id=1, email=email, created_at=DT)

    def authenticate(self, email, password):
        return self.authenticated_user


def test_register_success():

    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()

    response = client.post(
        "/auth/register",
        json={"email": "a@b.com", "password": "password123"},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "a@b.com"


def test_register_short_password_returns_422():

    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()

    response = client.post(
        "/auth/register",
        json={"email": "a@b.com", "password": "short"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_register_invalid_email_returns_422():

    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()

    response = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "password123"},
    )

    assert response.status_code == 422


def test_register_duplicate_returns_409():

    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService(exists=True)

    response = client.post(
        "/auth/register",
        json={"email": "a@b.com", "password": "password123"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_login_success_returns_token():

    user = SimpleNamespace(id=7, email="a@b.com", created_at=DT)
    app.dependency_overrides[get_auth_service] = (
        lambda: FakeAuthService(authenticated_user=user)
    )

    response = client.post(
        "/auth/login",
        json={"email": "a@b.com", "password": "pw"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_invalid_credentials_returns_401():

    app.dependency_overrides[get_auth_service] = (
        lambda: FakeAuthService(authenticated_user=None)
    )

    response = client.post(
        "/auth/login",
        json={"email": "a@b.com", "password": "wrong"},
    )

    assert response.status_code == 401


def test_protected_endpoint_requires_token():

    # No Authorization header -> 401 before any service/DB access.
    assert client.get("/dashboard/overview").status_code == 401
    assert client.get("/analytics/overview").status_code == 401
    assert client.get("/approvals/pending").status_code == 401