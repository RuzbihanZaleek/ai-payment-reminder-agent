"""Admin notification API: authn, authz, retry, discard."""

from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.admin.notifications import get_notification_recovery_service
from app.api.deps import get_current_user


client = TestClient(app)

DT = datetime(2026, 7, 28, 12, 0, 0)


def _notification(status="FAILED", outbox_id=1):
    return SimpleNamespace(
        id=outbox_id,
        contract_id=None,
        agent_run_id=None,
        channel="whatsapp",
        recipient="15551234567",
        status=status,
        attempt_count=3,
        last_error="boom",
        available_at=DT,
        sent_at=None,
        created_at=DT,
    )


class FakeRecoveryService:
    def __init__(self, retry_result="__default__", discard_result="__default__"):
        self._retry = _notification("PENDING") if retry_result == "__default__" else retry_result
        self._discard = _notification("DISCARDED") if discard_result == "__default__" else discard_result

    def list_failed(self):
        return [_notification("FAILED")]

    def list_pending(self):
        return [_notification("PENDING", outbox_id=2)]

    def retry(self, outbox_id):
        return self._retry

    def discard(self, outbox_id):
        return self._discard


def _as_admin():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, is_admin=True)


def _as_regular_user():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, is_admin=False)


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.clear()


def _install_service(service):
    app.dependency_overrides[get_notification_recovery_service] = lambda: service


# --- Authentication / authorization -----------------------------------------

def test_requires_authentication():
    # No token override -> real dependency -> 401.
    response = client.get("/admin/notifications/failed")
    assert response.status_code == 401


def test_non_admin_is_forbidden():
    _as_regular_user()
    _install_service(FakeRecoveryService())

    response = client.get("/admin/notifications/failed")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


# --- Listing ----------------------------------------------------------------

def test_admin_lists_failed():
    _as_admin()
    _install_service(FakeRecoveryService())

    response = client.get("/admin/notifications/failed")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["status"] == "FAILED"


def test_admin_lists_pending():
    _as_admin()
    _install_service(FakeRecoveryService())

    response = client.get("/admin/notifications/pending")

    assert response.status_code == 200
    assert response.json()[0]["status"] == "PENDING"


# --- Retry / discard --------------------------------------------------------

def test_retry_endpoint():
    _as_admin()
    _install_service(FakeRecoveryService())

    response = client.post("/admin/notifications/1/retry")

    assert response.status_code == 200
    assert response.json()["status"] == "PENDING"


def test_retry_missing_returns_404():
    _as_admin()
    _install_service(FakeRecoveryService(retry_result=None))

    response = client.post("/admin/notifications/999/retry")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOTIFICATION_NOT_FOUND"


def test_discard_endpoint():
    _as_admin()
    _install_service(FakeRecoveryService())

    response = client.post("/admin/notifications/1/discard")

    assert response.status_code == 200
    assert response.json()["status"] == "DISCARDED"


def test_discard_missing_returns_404():
    _as_admin()
    _install_service(FakeRecoveryService(discard_result=None))

    response = client.post("/admin/notifications/999/discard")

    assert response.status_code == 404


def test_v1_admin_route_also_works():
    _as_admin()
    _install_service(FakeRecoveryService())

    response = client.get("/api/v1/admin/notifications/failed")

    assert response.status_code == 200
