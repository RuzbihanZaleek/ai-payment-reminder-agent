from decimal import Decimal

from app.agents.balance_update_node import BalanceUpdateNode
from app.agents.state import AgentState


class FakeContract:

    def __init__(self, total_amount, daily_amount):
        self.total_amount = total_amount
        self.daily_amount = daily_amount


class FakeContractService:

    def __init__(self, contract):
        self.contract = contract
        self.get_called = False

    def get_contract(self, contract_id):

        self.get_called = True

        return self.contract


class FakePaymentService:

    def __init__(self, total_paid):
        self.total_paid = total_paid
        self.total_paid_called = False
        self.remaining_called = False

    def calculate_total_paid(self, contract_id):

        self.total_paid_called = True

        return self.total_paid

    def calculate_remaining_amount(self, total_amount, contract_id):

        self.remaining_called = True

        return total_amount - self.total_paid


def test_no_payment_id_skips_calculation():

    contract_service = FakeContractService(
        FakeContract(Decimal("1000"), Decimal("10"))
    )
    payment_service = FakePaymentService(
        Decimal("100")
    )

    node = BalanceUpdateNode(
        payment_service,
        contract_service,
    )

    state = AgentState(
        message="Paid something",
        contract_id=1,
        payment_id=None,
    )

    result = node.execute(state)

    assert contract_service.get_called is False
    assert payment_service.total_paid_called is False
    assert payment_service.remaining_called is False

    assert result.total_paid is None
    assert result.remaining_amount is None
    assert result.total_amount is None
    assert result.daily_amount is None


def test_updates_balance_from_existing_payments():

    contract_service = FakeContractService(
        FakeContract(Decimal("1000"), Decimal("10"))
    )
    payment_service = FakePaymentService(
        Decimal("350")
    )

    node = BalanceUpdateNode(
        payment_service,
        contract_service,
    )

    state = AgentState(
        message="I paid 50",
        contract_id=1,
        payment_id=42,
    )

    result = node.execute(state)

    assert payment_service.total_paid_called is True
    assert payment_service.remaining_called is True

    assert result.total_amount == Decimal("1000")
    assert result.daily_amount == Decimal("10")
    assert result.total_paid == Decimal("350")
    assert result.remaining_amount == Decimal("650")
