from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from types import SimpleNamespace

from app.main import app
from app.api.dashboard import get_dashboard_service, get_system_reporting_service
from app.api.deps import get_current_user


client = TestClient(app)


class FakeSystemReportingService:
    def get_system_stats(self):
        return {
            "notification_queue_size": 4,
            "failed_notification_count": 2,
            "oldest_pending_notification_age_seconds": 120.0,
            "scheduler_last_run": None,
            "scheduler_failure_count": 1,
        }


@pytest.fixture(autouse=True)
def _clear():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    yield
    app.dependency_overrides.clear()


class FakeDashboardService:

    def __init__(self, overview=None, exc=None):
        self.overview = overview
        self.exc = exc

    def get_overview(self, user_id):

        if self.exc is not None:
            raise self.exc

        return self.overview


def _overview():

    return {
        "contracts": {
            "total_contracts": 5,
            "active_contracts": 3,
            "completed_contracts": 2,
            "total_remaining_amount": Decimal("1500"),
        },
        "payments": {
            "payment_transaction_count": 12,
            "total_amount_received": Decimal("240"),
            "pending_review_count": 2,
            "pending_review_amount": Decimal("50"),
        },
        "agents": {"total_agent_runs": 20, "completed_runs": 18, "failed_runs": 2},
        "scheduler": {
            "total_scheduler_runs": 7,
            "failed_scheduler_runs": 1,
            "total_reminders_sent": 30,
            "total_reminders_failed": 3,
        },
    }


def test_overview_success():

    app.dependency_overrides[get_dashboard_service] = (
        lambda: FakeDashboardService(overview=_overview())
    )

    response = client.get("/dashboard/overview")

    assert response.status_code == 200

    data = response.json()
    assert data["contracts"]["total_contracts"] == 5
    assert data["payments"]["payment_transaction_count"] == 12
    assert data["payments"]["pending_review_count"] == 2
    assert Decimal(data["payments"]["total_amount_received"]) == Decimal("240")
    assert Decimal(data["payments"]["pending_review_amount"]) == Decimal("50")
    assert data["agents"]["completed_runs"] == 18
    assert data["scheduler"]["total_reminders_sent"] == 30
    assert data["scheduler"]["total_reminders_failed"] == 3


def test_overview_failure_returns_500():

    app.dependency_overrides[get_dashboard_service] = (
        lambda: FakeDashboardService(exc=RuntimeError("boom"))
    )

    # The router no longer catches -- the global handler standardizes the 500.
    # Disable TestClient's re-raise so we observe the handler's response.
    safe_client = TestClient(app, raise_server_exceptions=False)

    response = safe_client.get("/dashboard/overview")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"


def test_system_dashboard_requires_admin():
    # The autouse fixture logs in a non-admin user.
    app.dependency_overrides[get_system_reporting_service] = (
        lambda: FakeSystemReportingService()
    )

    response = client.get("/dashboard/system")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_system_dashboard_returns_queue_metrics_for_admin():
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=1, is_admin=True)
    )
    app.dependency_overrides[get_system_reporting_service] = (
        lambda: FakeSystemReportingService()
    )

    response = client.get("/dashboard/system")

    assert response.status_code == 200
    body = response.json()
    assert body["notification_queue_size"] == 4
    assert body["failed_notification_count"] == 2
    assert body["scheduler_failure_count"] == 1