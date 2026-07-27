from datetime import date
from decimal import Decimal

from app.agents.payment_creation_node import PaymentCreationNode
from app.agents.state import AgentState
from app.enums.payment_source import PaymentSource
from app.enums.payment_status import PaymentStatus
from app.enums.approval_status import ApprovalStatus


class FakeCreatedPayment:

    def __init__(self, payment_id):
        self.id = payment_id


class FakePaymentService:

    def __init__(self):
        self.created_payments = []

    def create_payment(self, payment):

        self.created_payments.append(payment)

        return FakeCreatedPayment(len(self.created_payments))


def _state(requires_approval, allocations):

    return AgentState(
        message="I paid 100 today",
        message_id="msg_123",
        requires_approval=requires_approval,
        pending_dates=[date.today()],
        payment_allocations=allocations,
    )


def test_does_not_create_payment_when_approval_required():

    service = FakePaymentService()
    node = PaymentCreationNode(service)

    state = _state(
        requires_approval=True,
        allocations=[{"contract_id": 1, "amount": Decimal("100.00")}],
    )

    result = node.execute(state)

    assert service.created_payments == []
    assert result.payment_id is None


def test_does_not_create_payment_when_no_allocations():

    service = FakePaymentService()
    node = PaymentCreationNode(service)

    state = _state(requires_approval=False, allocations=[])

    result = node.execute(state)

    assert service.created_payments == []
    assert result.payment_id is None


def test_creates_one_payment_per_allocation():

    service = FakePaymentService()
    node = PaymentCreationNode(service)

    state = _state(
        requires_approval=False,
        allocations=[
            {"contract_id": 1, "amount": Decimal("40.00")},
            {"contract_id": 2, "amount": Decimal("30.00")},
        ],
    )

    result = node.execute(state)

    assert len(service.created_payments) == 2

    first, second = service.created_payments

    assert first.contract_id == 1
    assert first.amount == Decimal("40.00")
    assert first.payment_date == date.today()
    assert first.source == PaymentSource.WHATSAPP_AI
    assert first.reference_message_id == "msg_123"
    assert first.notes == "I paid 100 today"

    # Auto-processed payments are confirmed (APPROVED, balance-affecting) and
    # need no manual review.
    assert first.status == PaymentStatus.APPROVED
    assert first.approval_status == ApprovalStatus.APPROVED
    assert first.requires_manual_review is False

    assert second.contract_id == 2
    assert second.amount == Decimal("30.00")
    assert second.approval_status == ApprovalStatus.APPROVED

    # First created payment id is retained for the downstream gate.
    assert result.payment_id == 1