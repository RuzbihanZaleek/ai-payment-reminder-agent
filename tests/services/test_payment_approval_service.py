from decimal import Decimal

from app.models.payment import Payment
from app.enums.payment_status import PaymentStatus
from app.enums.approval_status import ApprovalStatus
from app.services.payment_approval_service import PaymentApprovalService


OWNER_ID = 7


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


class FakeContract:

    def __init__(self, user_id):
        self.user_id = user_id


class FakeContractRepository:

    def __init__(self, owner_id=OWNER_ID):
        self.owner_id = owner_id

    def get_by_id(self, contract_id):
        return FakeContract(self.owner_id)


def _pending_payment():
    return Payment(
        id=1,
        contract_id=1,
        amount=Decimal("100.00"),
        status=PaymentStatus.PENDING,
        approval_status=ApprovalStatus.PENDING,
    )


def _service(payment_repo, owner_id=OWNER_ID):
    return PaymentApprovalService(payment_repo, FakeContractRepository(owner_id))


def test_approve_changes_status():

    payment = _pending_payment()
    repo = FakePaymentRepository(payment=payment)

    result = _service(repo).approve_payment(
        payment_id=1, approved_by="reviewer", user_id=OWNER_ID
    )

    assert result.status == PaymentStatus.APPROVED
    assert result.approval_status == ApprovalStatus.APPROVED
    assert result.approved_by == "reviewer"
    assert result.approved_at is not None
    assert repo.updated == [payment]


def test_reject_changes_status():

    payment = _pending_payment()
    repo = FakePaymentRepository(payment=payment)

    result = _service(repo).reject_payment(
        payment_id=1, rejected_by="reviewer", user_id=OWNER_ID
    )

    assert result.approval_status == ApprovalStatus.REJECTED
    assert result.status == PaymentStatus.REJECTED
    assert repo.updated == [payment]


def test_approve_missing_payment_returns_none():

    repo = FakePaymentRepository(payment=None)

    assert _service(repo).approve_payment(
        payment_id=999, approved_by="x", user_id=OWNER_ID
    ) is None
    assert repo.updated == []


def test_reject_missing_payment_returns_none():

    repo = FakePaymentRepository(payment=None)

    assert _service(repo).reject_payment(
        payment_id=999, rejected_by="x", user_id=OWNER_ID
    ) is None
    assert repo.updated == []


def test_approve_denied_for_non_owner():

    payment = _pending_payment()
    repo = FakePaymentRepository(payment=payment)

    # Contract belongs to OWNER_ID; a different user cannot approve it.
    result = _service(repo, owner_id=OWNER_ID).approve_payment(
        payment_id=1, approved_by="intruder", user_id=999
    )

    assert result is None
    assert repo.updated == []


def test_get_pending_approvals_scoped_to_owner():

    pending = [_pending_payment()]
    repo = FakePaymentRepository(pending=pending)

    # Owned by OWNER_ID -> returned for the owner, empty for others.
    assert _service(repo).get_pending_approvals(OWNER_ID) == pending
    assert _service(repo).get_pending_approvals(999) == []