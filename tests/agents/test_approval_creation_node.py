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


def _approval_state_without_contract(message: str) -> AgentState:

    # requires_approval with no single resolved contract -> cannot persist a
    # pending Payment (payments.contract_id is NOT NULL).
    return AgentState(
        message=message,
        message_id="msg_1",
        contract_id=None,
        requires_approval=True,
        payment_detection=_detection(),
    )


def test_no_payment_for_ambiguous_multi_contract_approval():

    service = FakePaymentService()
    node = ApprovalCreationNode(service)

    result = node.execute(
        _approval_state_without_contract("Paid INV001 and INV002")
    )

    assert service.created == []
    assert result.requires_approval is True


def test_no_payment_for_invalid_reference_approval():

    service = FakePaymentService()
    node = ApprovalCreationNode(service)

    result = node.execute(
        _approval_state_without_contract("Paid INV999 $20")
    )

    assert service.created == []
    assert result.requires_approval is True


def test_no_payment_for_uneven_payment_approval():

    service = FakePaymentService()
    node = ApprovalCreationNode(service)

    result = node.execute(
        _approval_state_without_contract("I paid 65")
    )

    assert service.created == []
    assert result.requires_approval is True


def test_no_payment_created_when_contract_id_missing():

    service = FakePaymentService()
    node = ApprovalCreationNode(service)

    result = node.execute(_approval_state_without_contract("I paid 100"))

    assert service.created == []
    # Approval state is preserved for a human to handle.
    assert result.requires_approval is True
    assert result.payment_id is None
