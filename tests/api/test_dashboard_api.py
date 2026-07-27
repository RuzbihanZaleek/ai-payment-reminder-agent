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

    response = client.get("/dashboard/overview")

    assert response.status_code == 500