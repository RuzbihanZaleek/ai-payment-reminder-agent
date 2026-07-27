from decimal import Decimal

from app.agents.payment_receipt_node import PaymentReceiptNode
from app.agents.state import AgentState


class FakeReceiptService:

    def __init__(self):
        self.calls = []
        self.receipts = [{"reference_code": "INV001", "previous_balance": Decimal("900"), "new_balance": Decimal("880")}]

    def generate_receipts(self, agent_run_id, payment_allocations):

        self.calls.append((agent_run_id, payment_allocations))

        return self.receipts


def test_creates_receipts_and_stores_on_state():

    service = FakeReceiptService()
    node = PaymentReceiptNode(service)

    allocations = [{"contract_id": 1, "amount": Decimal("20"), "payment_id": 5}]

    state = AgentState(
        message="Paid 20",
        agent_run_id=7,
        requires_approval=False,
        payment_allocations=allocations,
    )

    result = node.execute(state)

    assert service.calls == [(7, allocations)]
    assert result.payment_receipts == service.receipts


def test_no_receipt_on_approval_path():

    service = FakeReceiptService()
    node = PaymentReceiptNode(service)

    state = AgentState(
        message="Paid something",
        agent_run_id=7,
        requires_approval=True,
        payment_allocations=[{"contract_id": 1, "amount": Decimal("20")}],
    )

    result = node.execute(state)

    assert service.calls == []
    assert result.payment_receipts == []


def test_no_receipt_when_no_allocations():

    service = FakeReceiptService()
    node = PaymentReceiptNode(service)

    state = AgentState(
        message="Hi",
        agent_run_id=7,
        requires_approval=False,
        payment_allocations=[],
    )

    result = node.execute(state)

    assert service.calls == []
    assert result.payment_receipts == []