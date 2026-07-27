from decimal import Decimal

from app.services.payment_allocation_service import PaymentAllocationService


class FakePaymentService:

    def __init__(self, remaining_by_id):
        self.remaining_by_id = remaining_by_id

    def calculate_remaining_amount(self, total_amount, contract_id):

        return self.remaining_by_id.get(contract_id, Decimal("0"))


def _contract(contract_id, daily=Decimal("10"), total=Decimal("1000")):

    return {"id": contract_id, "daily_amount": daily, "total_amount": total}


def _service(remaining_by_id):

    return PaymentAllocationService(FakePaymentService(remaining_by_id))


def _as_map(result):

    return {a["contract_id"]: a["amount"] for a in result["allocations"]}


def test_one_contract_gets_full_amount():

    service = _service({1: Decimal("500")})

    result = service.allocate(Decimal("100"), [_contract(1)])

    assert result["requires_approval"] is False
    assert _as_map(result) == {1: Decimal("100")}


def test_two_contracts_round_robin():

    # The spec example: INV001 & INV002 daily 10, payment 70 -> 40 / 30.
    service = _service({1: Decimal("1000"), 2: Decimal("1000")})

    result = service.allocate(Decimal("70"), [_contract(1), _contract(2)])

    assert result["requires_approval"] is False
    assert _as_map(result) == {1: Decimal("40"), 2: Decimal("30")}


def test_three_contracts_even_split():

    service = _service({1: Decimal("1000"), 2: Decimal("1000"), 3: Decimal("1000")})

    result = service.allocate(
        Decimal("60"),
        [_contract(1), _contract(2), _contract(3)],
    )

    assert result["requires_approval"] is False
    assert _as_map(result) == {1: Decimal("20"), 2: Decimal("20"), 3: Decimal("20")}


def test_round_robin_remainder_goes_to_earlier_contracts():

    # 70 across 3 daily-10 contracts -> 30 / 20 / 20.
    service = _service({1: Decimal("1000"), 2: Decimal("1000"), 3: Decimal("1000")})

    result = service.allocate(
        Decimal("70"),
        [_contract(1), _contract(2), _contract(3)],
    )

    assert _as_map(result) == {1: Decimal("30"), 2: Decimal("20"), 3: Decimal("20")}


def test_explicit_reference_allocates_full_amount():

    # remaining is irrelevant when a contract was explicitly referenced.
    service = _service({})

    result = service.allocate(
        Decimal("100"),
        [_contract(1), _contract(2)],
        resolved_contract_id=2,
    )

    assert result["requires_approval"] is False
    assert _as_map(result) == {2: Decimal("100")}


def test_completed_contracts_are_ignored():

    # Contract 1 is fully paid (remaining 0) -> only contract 2 is eligible.
    service = _service({1: Decimal("0"), 2: Decimal("500")})

    result = service.allocate(Decimal("100"), [_contract(1), _contract(2)])

    assert result["requires_approval"] is False
    assert _as_map(result) == {2: Decimal("100")}


def test_invalid_amount_requires_approval():

    service = _service({1: Decimal("1000"), 2: Decimal("1000")})

    # 65 is not a whole number of daily-10 units.
    result = service.allocate(Decimal("65"), [_contract(1), _contract(2)])

    assert result["requires_approval"] is True
    assert result["allocations"] == []


def test_non_positive_amount_requires_approval():

    service = _service({1: Decimal("1000"), 2: Decimal("1000")})

    result = service.allocate(Decimal("0"), [_contract(1), _contract(2)])

    assert result["requires_approval"] is True
    assert result["allocations"] == []


def test_no_eligible_contracts_requires_approval():

    service = _service({1: Decimal("0"), 2: Decimal("0")})

    result = service.allocate(Decimal("100"), [_contract(1), _contract(2)])

    assert result["requires_approval"] is True
    assert result["allocations"] == []