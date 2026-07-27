from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.dashboard import get_dashboard_service


client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.clear()


class FakeDashboardService:

    def __init__(self, overview=None, exc=None):
        self.overview = overview
        self.exc = exc

    def get_overview(self):

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
        "payments": {"total_payments_received": 12, "pending_approval_count": 2},
        "agents": {"total_agent_runs": 20, "completed_runs": 18, "failed_runs": 2},
        "scheduler": {"total_scheduler_runs": 7, "successful_runs": 6, "failed_runs": 1},
    }


def test_overview_success():

    app.dependency_overrides[get_dashboard_service] = (
        lambda: FakeDashboardService(overview=_overview())
    )

    response = client.get("/dashboard/overview")

    assert response.status_code == 200

    data = response.json()
    assert data["contracts"]["total_contracts"] == 5
    assert data["payments"]["pending_approval_count"] == 2
    assert data["agents"]["completed_runs"] == 18
    assert data["scheduler"]["successful_runs"] == 6


def test_overview_failure_returns_500():

    app.dependency_overrides[get_dashboard_service] = (
        lambda: FakeDashboardService(exc=RuntimeError("boom"))
    )

    response = client.get("/dashboard/overview")

    assert response.status_code == 500