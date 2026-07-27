from decimal import Decimal

from app.services.payment_allocation_formatter import PaymentAllocationFormatter


def test_single_allocation():

    formatter = PaymentAllocationFormatter()

    text = formatter.format(
        [{"contract_id": 1, "reference_code": "INV001", "amount": Decimal("20")}]
    )

    assert text == "INV001: $20"


def test_multiple_allocations():

    formatter = PaymentAllocationFormatter()

    text = formatter.format(
        [
            {"contract_id": 1, "reference_code": "INV001", "amount": Decimal("20")},
            {"contract_id": 2, "reference_code": "INV002", "amount": Decimal("10")},
        ]
    )

    assert text == "INV001: $20\nINV002: $10"


def test_formats_whole_and_fractional_amounts():

    formatter = PaymentAllocationFormatter()

    text = formatter.format(
        [
            {"contract_id": 1, "reference_code": "INV001", "amount": Decimal("2100")},
            {"contract_id": 2, "reference_code": "INV002", "amount": Decimal("99.50")},
        ]
    )

    assert text == "INV001: $2,100\nINV002: $99.50"


def test_missing_reference_code_falls_back():

    formatter = PaymentAllocationFormatter()

    text = formatter.format([{"contract_id": 1, "amount": Decimal("20")}])

    assert text == "Contract: $20"