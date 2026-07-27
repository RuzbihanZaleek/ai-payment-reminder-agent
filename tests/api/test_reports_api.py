from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.reports.contracts import (
    get_contract_reporting_service,
    get_payment_reporting_service,
    get_receipt_reporting_service,
)
from app.api.reports.agent_runs import get_agent_reporting_service
from app.api.reports.scheduler_runs import get_scheduler_reporting_service
from app.api.deps import get_current_user, require_owned_contract
from app.repositories.pagination import PageResult


client = TestClient(app)


def _page(items):
    return PageResult(items=items, total=len(items))

DT = datetime(2026, 7, 27, 12, 0, 0)
D = date(2026, 7, 27)


@pytest.fixture(autouse=True)
def _clear():
    # Authenticated user + contract ownership are exercised separately; these
    # tests focus on the reporting behavior, so both are stubbed.
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    app.dependency_overrides[require_owned_contract] = lambda: SimpleNamespace(id=1, user_id=1)
    yield
    app.dependency_overrides.clear()


class _Svc:
    """Minimal stub exposing one method returning a preset value."""

    def __init__(self, method_name, value):
        setattr(self, method_name, lambda *a, **k: value)


# --- Contract summary -------------------------------------------------------

def test_contract_summary_success():

    summary = {
        "contract_id": 1,
        "reference_code": "INV001",
        "name": "Friend Payment",
        "total_amount": Decimal("1000"),
        "total_paid": Decimal("120"),
        "remaining_amount": Decimal("880"),
        "payment_count": 2,
    }
    app.dependency_overrides[get_contract_reporting_service] = (
        lambda: _Svc("get_contract_summary", summary)
    )

    response = client.get("/reports/contracts/1")

    assert response.status_code == 200
    data = response.json()
    assert data["reference_code"] == "INV001"
    assert data["payment_count"] == 2


def test_contract_summary_not_found_returns_404():

    app.dependency_overrides[get_contract_reporting_service] = (
        lambda: _Svc("get_contract_summary", None)
    )

    response = client.get("/reports/contracts/999")

    assert response.status_code == 404


# --- Payment history --------------------------------------------------------

def test_contract_payments_success():

    payments = [
        {
            "id": 1,
            "contract_id": 1,
            "amount": Decimal("20"),
            "payment_date": D,
            "status": "APPROVED",
            "approval_status": "APPROVED",
            "source": "WHATSAPP_AI",
            "created_at": DT,
        }
    ]
    app.dependency_overrides[get_payment_reporting_service] = (
        lambda: _Svc("get_payment_history", _page(payments))
    )

    response = client.get("/reports/contracts/1/payments")

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total_items"] == 1
    assert len(body["items"]) == 1


# --- Receipt history --------------------------------------------------------

def test_contract_receipts_success():

    receipts = [
        {
            "id": 1,
            "contract_id": 1,
            "payment_id": 5,
            "amount": Decimal("20"),
            "previous_balance": Decimal("900"),
            "new_balance": Decimal("880"),
            "allocation_summary": "INV001: $20",
            "created_at": DT,
        }
    ]
    app.dependency_overrides[get_receipt_reporting_service] = (
        lambda: _Svc("get_receipt_history", _page(receipts))
    )

    response = client.get("/reports/contracts/1/receipts")

    assert response.status_code == 200
    items = response.json()["items"]
    assert items[0]["new_balance"] == "880.00" or items[0]["new_balance"] == "880"


# --- Agent runs -------------------------------------------------------------

def _agent_run():
    return {
        "id": 3,
        "contract_id": 1,
        "message_id": "msg_1",
        "status": "COMPLETED",
        "current_step": None,
        "created_at": DT,
        "completed_at": DT,
    }


def test_agent_runs_list_success():

    class FakeAgentSvc:
        def get_recent_runs(self, user_id, run_filter, page, page_size, order):
            return _page([_agent_run()])

    app.dependency_overrides[get_agent_reporting_service] = lambda: FakeAgentSvc()

    response = client.get("/reports/agent-runs")

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == 3


def test_agent_run_detail_success():

    details = {
        "run": _agent_run(),
        "events": [
            {
                "id": 1,
                "agent_run_id": 3,
                "node_name": "PaymentCreationNode",
                "status": "COMPLETED",
                "message": None,
                "duration_ms": 12,
                "created_at": DT,
            }
        ],
    }
    app.dependency_overrides[get_agent_reporting_service] = (
        lambda: _Svc("get_run_details", details)
    )

    response = client.get("/reports/agent-runs/3")

    assert response.status_code == 200
    body = response.json()
    assert body["run"]["id"] == 3
    assert len(body["events"]) == 1


def test_agent_run_detail_not_found_returns_404():

    app.dependency_overrides[get_agent_reporting_service] = (
        lambda: _Svc("get_run_details", None)
    )

    response = client.get("/reports/agent-runs/999")

    assert response.status_code == 404


# --- Scheduler runs ---------------------------------------------------------

def _scheduler_run():
    return {
        "id": 4,
        "run_type": "daily_reminders",
        "status": "COMPLETED",
        "started_at": DT,
        "completed_at": DT,
        "total_contracts": 2,
        "successful_count": 2,
        "failed_count": 0,
    }


def test_scheduler_runs_list_success():

    class FakeSchedSvc:
        def get_recent_runs(self, run_filter, page, page_size, order):
            return _page([_scheduler_run()])

    app.dependency_overrides[get_scheduler_reporting_service] = lambda: FakeSchedSvc()

    response = client.get("/reports/scheduler-runs")

    assert response.status_code == 200
    assert response.json()["items"][0]["run_type"] == "daily_reminders"


def test_scheduler_run_detail_success():

    details = {
        "run": _scheduler_run(),
        "events": [
            {
                "id": 1,
                "scheduler_run_id": 4,
                "contract_id": 1,
                "status": "SENT",
                "message": None,
                "created_at": DT,
            }
        ],
    }
    app.dependency_overrides[get_scheduler_reporting_service] = (
        lambda: _Svc("get_run_details", details)
    )

    response = client.get("/reports/scheduler-runs/4")

    assert response.status_code == 200
    assert response.json()["run"]["id"] == 4


def test_scheduler_run_detail_not_found_returns_404():

    app.dependency_overrides[get_scheduler_reporting_service] = (
        lambda: _Svc("get_run_details", None)
    )

    response = client.get("/reports/scheduler-runs/999")

    assert response.status_code == 404