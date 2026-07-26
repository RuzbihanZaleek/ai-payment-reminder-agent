from decimal import Decimal

from app.agents.approval_creation_node import ApprovalCreationNode
from app.agents.state import AgentState
from app.enums.payment_status import PaymentStatus
from app.enums.approval_status import ApprovalStatus
from app.schemas.payment_detection import (
    PaymentDetectionResult,
    PaymentIntent,
)


class FakePaymentService:

    def __init__(self):
        self.created = []

    def create_payment(self, payment):

        payment.id = 1
        self.created.append(payment)

        return payment


def _detection() -> PaymentDetectionResult:

    return PaymentDetectionResult(
        intent=PaymentIntent.PAYMENT_RECEIVED,
        amount=Decimal("100.00"),
        currency="USD",
        confidence=0.50,
    )


def test_creates_approval_when_confidence_low():

    service = FakePaymentService()
    node = ApprovalCreationNode(service)

    state = AgentState(
        message="I paid 100",
        message_id="msg_1",
        contract_id=1,
        requires_approval=True,
        payment_detection=_detection(),
    )

    result = node.execute(state)

    assert len(service.created) == 1

    created = service.created[0]

    assert created.status == PaymentStatus.PENDING
    assert created.approval_status == ApprovalStatus.PENDING
    assert created.amount == Decimal("100.00")
    assert created.contract_id == 1

    # A pending approval must NOT become an approved payment
    assert result.payment_id is None


def test_no_approval_when_confidence_high():

    service = FakePaymentService()
    node = ApprovalCreationNode(service)

    state = AgentState(
        message="I paid 100",
        message_id="msg_1",
        contract_id=1,
        requires_approval=False,
        payment_detection=_detection(),
    )

    result = node.execute(state)

    assert service.created == []
    assert result.payment_id is None
