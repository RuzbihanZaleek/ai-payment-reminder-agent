from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.approval import get_payment_approval_service
from app.api.deps import get_current_user
from app.models.payment import Payment
from app.enums.payment_status import PaymentStatus
from app.enums.approval_status import ApprovalStatus
from app.repositories.pagination import PageResult


client = TestClient(app)


class FakeApprovalService:

    def __init__(self, pending=None, payment=None):
        self.pending = pending or []
        self.payment = payment
        self.approved = []
        self.rejected = []
        self.approvals_calls = []

    def get_approvals_page(self, user_id, approval_status, page, page_size, order):

        self.approvals_calls.append((user_id, approval_status, page, page_size, order))

        return PageResult(items=self.pending, total=len(self.pending))

    def approve_payment(self, payment_id, approved_by, user_id):

        self.approved.append((payment_id, approved_by))

        return self.payment

    def reject_payment(self, payment_id, rejected_by, user_id):

        self.rejected.append((payment_id, rejected_by))

        return self.payment


def _payment(status=PaymentStatus.PENDING, approval_status=ApprovalStatus.PENDING):

    return Payment(
        id=1,
        contract_id=7,
        amount=Decimal("100.00"),
        status=status,
        approval_status=approval_status,
    )


@pytest.fixture
def override_service():

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)

    def _install(service):
        app.dependency_overrides[get_payment_approval_service] = lambda: service
        return service

    yield _install

    app.dependency_overrides.clear()


def test_list_pending_approvals(override_service):

    override_service(FakeApprovalService(pending=[_payment()]))

    response = client.get("/approvals/pending")

    assert response.status_code == 200

    data = response.json()

    assert data["meta"]["total_items"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == 1
    assert data["items"][0]["approval_status"] == "PENDING"


def test_approve_changes_status(override_service):

    approved = _payment(
        status=PaymentStatus.APPROVED,
        approval_status=ApprovalStatus.APPROVED,
    )
    service = override_service(FakeApprovalService(payment=approved))

    response = client.post(
        "/approvals/1/approve",
        json={"reviewed_by": "boss"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "APPROVED"
    assert data["approval_status"] == "APPROVED"
    assert service.approved == [(1, "boss")]


def test_reject_changes_status(override_service):

    rejected = _payment(
        status=PaymentStatus.PENDING,
        approval_status=ApprovalStatus.REJECTED,
    )
    service = override_service(FakeApprovalService(payment=rejected))

    response = client.post(
        "/approvals/1/reject",
        json={"reviewed_by": "boss"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["approval_status"] == "REJECTED"
    assert data["status"] == "PENDING"
    assert service.rejected == [(1, "boss")]


def test_approve_missing_reviewer_returns_422(override_service):

    override_service(FakeApprovalService(payment=_payment()))

    response = client.post("/approvals/1/approve", json={})

    assert response.status_code == 422


def test_approve_unknown_payment_returns_404(override_service):

    override_service(FakeApprovalService(payment=None))

    response = client.post(
        "/approvals/999/approve",
        json={"reviewed_by": "boss"},
    )

    assert response.status_code == 404
