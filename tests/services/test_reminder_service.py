from decimal import Decimal

from app.models.contract import ContractStatus
from app.services.reminder_service import ReminderService


class FakeContract:

    def __init__(self, contract_id, total_amount, status):
        self.id = contract_id
        self.total_amount = total_amount
        self.status = status


class FakeContractService:

    def __init__(self, contracts):
        self.contracts = contracts

    def get_all_contracts(self):

        return self.contracts


class FakePaymentService:

    def __init__(self, remaining_by_contract):
        self.remaining_by_contract = remaining_by_contract

    def calculate_remaining_amount(self, total_amount, contract_id):

        return self.remaining_by_contract[contract_id]


def test_pending_contracts_returned():

    active_with_balance = FakeContract(1, Decimal("1000"), ContractStatus.ACTIVE)

    contract_service = FakeContractService([active_with_balance])
    payment_service = FakePaymentService({1: Decimal("500")})

    service = ReminderService(contract_service, payment_service)

    assert service.get_pending_reminders() == [active_with_balance]


def test_completed_contracts_ignored():

    active_with_balance = FakeContract(1, Decimal("1000"), ContractStatus.ACTIVE)
    completed = FakeContract(2, Decimal("1000"), ContractStatus.COMPLETED)
    active_fully_paid = FakeContract(3, Decimal("1000"), ContractStatus.ACTIVE)

    contract_service = FakeContractService(
        [active_with_balance, completed, active_fully_paid]
    )
    payment_service = FakePaymentService(
        {
            1: Decimal("500"),   # active + owes -> reminder
            2: Decimal("500"),   # completed -> ignored despite balance
            3: Decimal("0"),     # active but fully paid -> ignored
        }
    )

    service = ReminderService(contract_service, payment_service)

    assert service.get_pending_reminders() == [active_with_balance]
