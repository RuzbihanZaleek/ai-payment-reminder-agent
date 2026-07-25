from datetime import date
from decimal import Decimal

from app.agents.payment_creation_node import PaymentCreationNode
from app.agents.state import AgentState
from app.enums.payment_source import PaymentSource
from app.schemas.payment_detection import (
    PaymentDetectionResult,
    PaymentIntent,
)


class FakeCreatedPayment:

    def __init__(self):
        self.id = 1


class FakePaymentService:

    def __init__(self):
        self.create_called = False
        self.created_payment = None

    def create_payment(self, payment):

        self.create_called = True
        self.created_payment = payment

        return FakeCreatedPayment()


def create_state(
    requires_approval: bool,
) -> AgentState:

    return AgentState(
        message="I paid 100 today",
        message_id="msg_123",
        contract_id=1,
        requires_approval=requires_approval,
        pending_dates=[date.today()],
        payment_detection=PaymentDetectionResult(
            intent=PaymentIntent.PAYMENT_RECEIVED,
            amount=Decimal("100.00"),
            currency="USD",
            confidence=0.95,
        ),
    )


def test_does_not_create_payment_when_approval_required():

    service = FakePaymentService()

    node = PaymentCreationNode(service)

    state = create_state(True)

    result = node.execute(state)

    assert service.create_called is False
    assert result.payment_id is None


def test_creates_payment_when_approved():

    service = FakePaymentService()

    node = PaymentCreationNode(service)

    state = create_state(False)

    result = node.execute(state)

    assert service.create_called is True

    assert result.payment_id == 1

    payment = service.created_payment

    assert payment.contract_id == 1
    assert payment.amount == Decimal("100.00")
    assert payment.payment_date == date.today()
    assert payment.source == PaymentSource.WHATSAPP_AI
    assert payment.reference_message_id == "msg_123"
    assert payment.notes == "I paid 100 today"