from decimal import Decimal

from app.services.payment_receipt_service import PaymentReceiptService
from app.services.payment_allocation_formatter import PaymentAllocationFormatter


class FakeContract:

    def __init__(self, total_amount, reference_code):
        self.total_amount = total_amount
        self.reference_code = reference_code


class FakeContractService:

    def __init__(self, contracts_by_id):
        self.contracts_by_id = contracts_by_id

    def get_contract(self, contract_id):

        return self.contracts_by_id.get(contract_id)


class FakePaymentService:

    def __init__(self, remaining_by_id):
        self.remaining_by_id = remaining_by_id

    def calculate_remaining_amount(self, total_amount, contract_id):

        return self.remaining_by_id[contract_id]


class FakePaymentReceiptRepository:

    def __init__(self):
        self.created = []

    def create(self, receipt):

        self.created.append(receipt)

        return receipt


def _service(contracts_by_id, remaining_by_id):

    return PaymentReceiptService(
        FakePaymentReceiptRepository(),
        FakeContractService(contracts_by_id),
        FakePaymentService(remaining_by_id),
        PaymentAllocationFormatter(),
    )


def test_single_contract_receipt():

    service = _service(
        {1: FakeContract(Decimal("1000"), "INV001")},
        {1: Decimal("900")},
    )

    allocations = [
        {"contract_id": 1, "reference_code": "INV001", "amount": Decimal("20"), "payment_id": 5},
    ]

    receipts = service.generate_receipts(agent_run_id=7, payment_allocations=allocations)

    assert len(receipts) == 1
    r = receipts[0]
    assert r["reference_code"] == "INV001"
    assert r["previous_balance"] == Decimal("900")
    assert r["new_balance"] == Decimal("880")

    # A PaymentReceipt row was persisted with the audit fields.
    stored = service.payment_receipt_repository.created[0]
    assert stored.agent_run_id == 7
    assert stored.contract_id == 1
    assert stored.payment_id == 5
    assert stored.amount == Decimal("20")
    assert stored.previous_balance == Decimal("900")
    assert stored.new_balance == Decimal("880")


def test_multiple_contract_receipts():

    service = _service(
        {
            1: FakeContract(Decimal("1000"), "INV001"),
            2: FakeContract(Decimal("1000"), "INV002"),
        },
        {1: Decimal("900"), 2: Decimal("1000")},
    )

    allocations = [
        {"contract_id": 1, "reference_code": "INV001", "amount": Decimal("40"), "payment_id": 5},
        {"contract_id": 2, "reference_code": "INV002", "amount": Decimal("30"), "payment_id": 6},
    ]

    receipts = service.generate_receipts(agent_run_id=7, payment_allocations=allocations)

    assert len(receipts) == 2
    assert receipts[0]["reference_code"] == "INV001"
    assert receipts[0]["previous_balance"] == Decimal("900")
    assert receipts[0]["new_balance"] == Decimal("860")
    assert receipts[1]["reference_code"] == "INV002"
    assert receipts[1]["previous_balance"] == Decimal("1000")
    assert receipts[1]["new_balance"] == Decimal("970")

    # Both audit rows carry the shared allocation summary.
    stored = service.payment_receipt_repository.created
    assert len(stored) == 2
    assert stored[0].allocation_summary == "INV001: $40\nINV002: $30"