from decimal import Decimal

from app.models.payment import Payment
from app.enums.payment_status import PaymentStatus
from app.enums.approval_status import ApprovalStatus
from app.services.payment_approval_service import PaymentApprovalService


class FakePaymentRepository:

    def __init__(self, payment=None, pending=None):
        self.payment = payment
        self.pending = pending or []
        self.updated = []

    def get_by_id(self, payment_id):

        return self.payment

    def get_by_approval_status(self, approval_status):

        return self.pending

    def update(self, payment):

        self.updated.append(payment)

        return payment


def _pending_payment():

    return Payment(
        id=1,
        contract_id=1,
        amount=Decimal("100.00"),
        status=PaymentStatus.PENDING,
        approval_status=ApprovalStatus.PENDING,
    )


def test_approve_changes_status():

    payment = _pending_payment()
    repo = FakePaymentRepository(payment=payment)

    service = PaymentApprovalService(repo)

    result = service.approve_payment(payment_id=1, approved_by="reviewer")

    assert result.status == PaymentStatus.APPROVED
    assert result.approval_status == ApprovalStatus.APPROVED
    assert result.approved_by == "reviewer"
    assert result.approved_at is not None
    assert repo.updated == [payment]


def test_reject_changes_status():

    payment = _pending_payment()
    repo = FakePaymentRepository(payment=payment)

    service = PaymentApprovalService(repo)

    result = service.reject_payment(payment_id=1, rejected_by="reviewer")

    # Rejection is terminal on both axes so the payment never affects balance.
    assert result.approval_status == ApprovalStatus.REJECTED
    assert result.status == PaymentStatus.REJECTED
    assert repo.updated == [payment]


def test_approve_missing_payment_returns_none():

    repo = FakePaymentRepository(payment=None)

    service = PaymentApprovalService(repo)

    assert service.approve_payment(payment_id=999, approved_by="x") is None
    assert repo.updated == []


def test_reject_missing_payment_returns_none():

    repo = FakePaymentRepository(payment=None)

    service = PaymentApprovalService(repo)

    assert service.reject_payment(payment_id=999, rejected_by="x") is None
    assert repo.updated == []


def test_get_pending_approvals():

    pending = [_pending_payment()]
    repo = FakePaymentRepository(pending=pending)

    service = PaymentApprovalService(repo)

    assert service.get_pending_approvals() == pending
