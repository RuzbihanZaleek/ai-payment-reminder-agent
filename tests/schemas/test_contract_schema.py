from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.schemas.contract import ContractCreate


def valid_contract_data():
    return {
        "name": "Friend Payment",
        "description": "Monthly repayment tracking",
        "total_amount": Decimal("2200"),
        "daily_amount": Decimal("20"),
        "currency": "USD",
        "start_date": date.today(),
        "whatsapp_chat_id": "friend_chat_123"
    }


def test_valid_contract_creation():

    contract = ContractCreate(
        **valid_contract_data()
    )

    assert contract.name == "Friend Payment"
    assert contract.total_amount == Decimal("2200")


def test_negative_total_amount_should_fail():

    data = valid_contract_data()

    data["total_amount"] = Decimal("-100")

    with pytest.raises(ValueError):
        ContractCreate(**data)


def test_daily_amount_greater_than_total_should_fail():

    data = valid_contract_data()

    data["daily_amount"] = Decimal("5000")

    with pytest.raises(ValueError):
        ContractCreate(**data)


def test_future_start_date_should_fail():

    data = valid_contract_data()

    data["start_date"] = date.today() + timedelta(days=1)

    with pytest.raises(ValueError):
        ContractCreate(**data)


def test_end_date_before_start_date_should_fail():

    data = valid_contract_data()

    data["end_date"] = date.today() - timedelta(days=1)

    with pytest.raises(ValueError):
        ContractCreate(**data)