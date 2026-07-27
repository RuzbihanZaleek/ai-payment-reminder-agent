"""Phase 9.2 - payment lifecycle consistency.

Verifies that a payment's `status` (which drives the balance) stays aligned with
how the payment was created / reviewed:

- AI-confirmed payment (status=APPROVED)  -> reduces remaining balance.
- Manual-review payment (status=PENDING)  -> does not.
- Approval (status -> APPROVED)           -> reduces.
- Rejection (status -> REJECTED)          -> does not.
"""

from datetime import date
from decimal import Decimal

from app.models.payment import Payment
from app.enums.payment_status import PaymentStatus
from app.enums.approval_status import ApprovalStatus
from app.services.payment_service import PaymentService
from app.services.payment_approval_service import PaymentApprovalService


class FakePaymentRepository:

    def __init__(self, payments):
        self.payments = list(payments)
        self._next_id = len(self.payments) + 1

    def get_by_contract_id(self, contract_id):
        return [p for p in self.payments if p.contract_id == contract_id]

    def get_by_id(self, payment_id):
        return next((p for p in self.payments if p.id == payment_id), None)

    def update(self, payment):
        return payment


def _payment(payment_id, status, approval_status, amount=Decimal("100"), manual=False):

    return Payment(
        id=payment_id,
        contract_id=1,
        amount=amount,
        payment_date=date.today(),
        status=status,
        approval_status=approval_status,
        requires_manual_review=manual,
    )


def test_ai_confirmed_payment_reduces_balance():

    service = PaymentService(
        FakePaymentRepository([
            _payment(1, PaymentStatus.APPROVED, ApprovalStatus.APPROVED, Decimal("40")),
        ])
    )

    remaining = service.calculate_remaining_amount(Decimal("1000"), 1)

    assert remaining == Decimal("960")


def test_manual_review_payment_does_not_reduce_balance():

    service = PaymentService(
        FakePaymentRepository([
            _payment(1, PaymentStatus.PENDING, ApprovalStatus.PENDING, Decimal("40"), manual=True),
        ])
    )

    remaining = service.calculate_remaining_amount(Decimal("1000"), 1)

    assert remaining == Decimal("1000")


def test_approval_reduces_balance():

    payment = _payment(1, PaymentStatus.PENDING, ApprovalStatus.PENDING, Decimal("40"), manual=True)
    repo = FakePaymentRepository([payment])

    PaymentApprovalService(repo).approve_payment(payment_id=1, approved_by="boss")

    remaining = PaymentService(repo).calculate_remaining_amount(Decimal("1000"), 1)

    assert payment.status == PaymentStatus.APPROVED
    assert remaining == Decimal("960")


def test_rejection_does_not_reduce_balance():

    payment = _payment(1, PaymentStatus.PENDING, ApprovalStatus.PENDING, Decimal("40"), manual=True)
    repo = FakePaymentRepository([payment])

    PaymentApprovalService(repo).reject_payment(payment_id=1, rejected_by="boss")

    remaining = PaymentService(repo).calculate_remaining_amount(Decimal("1000"), 1)

    assert payment.status == PaymentStatus.REJECTED
    assert remaining == Decimal("1000")