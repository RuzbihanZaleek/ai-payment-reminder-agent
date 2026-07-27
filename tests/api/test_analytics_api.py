from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.analytics import get_analytics_service


client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.clear()


class FakeAnalyticsService:

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
            "total_contract_value": Decimal("1000"),
            "total_collected_amount": Decimal("600"),
            "total_outstanding_amount": Decimal("400"),
            "collection_rate": 0.6,
        },
        "payments": {
            "total_amount_received": Decimal("200"),
            "payment_transaction_count": 4,
            "average_payment_amount": Decimal("50"),
            "pending_review_amount": Decimal("25"),
        },
        "reminders": {
            "total_reminders_logged": 12,
            "total_reminders_sent": 9,
            "total_reminders_failed": 3,
            "delivery_rate": 0.75,
        },
        "agents": {
            "total_agent_runs": 10,
            "completed_runs": 8,
            "failed_runs": 2,
            "success_rate": 0.8,
        },
    }


def test_overview_success():

    app.dependency_overrides[get_analytics_service] = (
        lambda: FakeAnalyticsService(overview=_overview())
    )

    response = client.get("/analytics/overview")

    assert response.status_code == 200

    data = response.json()
    assert data["contracts"]["collection_rate"] == 0.6
    assert data["payments"]["payment_transaction_count"] == 4
    assert data["reminders"]["delivery_rate"] == 0.75
    assert data["agents"]["success_rate"] == 0.8
    assert Decimal(data["contracts"]["total_collected_amount"]) == Decimal("600")


def test_overview_failure_returns_500():

    app.dependency_overrides[get_analytics_service] = (
        lambda: FakeAnalyticsService(exc=RuntimeError("boom"))
    )

    response = client.get("/analytics/overview")

    assert response.status_code == 500