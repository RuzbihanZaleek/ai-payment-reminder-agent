from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from app.models.contract import Contract
from app.schemas.contract import ContractCreate, Currency
from app.services.contract_service import ContractService


def test_create_contract():

    # Fake repository
    repository = Mock()


    # Expected database object
    repository.create.return_value = Contract(
        id=1,
        name="Friend Payment",
        total_amount=Decimal("2200"),
        daily_amount=Decimal("20"),
        currency="USD",
        start_date=date.today(),
        whatsapp_chat_id="friend_chat_123"
    )


    service = ContractService(repository)


    contract_data = ContractCreate(
        name="Friend Payment",
        total_amount=Decimal("2200"),
        daily_amount=Decimal("20"),
        currency=Currency.USD,
        start_date=date.today(),
        whatsapp_chat_id="friend_chat_123"
    )


    result = service.create_contract(contract_data)


    assert result.id == 1
    assert result.name == "Friend Payment"


    repository.create.assert_called_once()
    
def test_get_contract():

    repository = Mock()

    expected_contract = Contract(
        id=1,
        name="Friend Payment",
        total_amount=Decimal("2200"),
        daily_amount=Decimal("20"),
        currency="USD",
        start_date=date.today(),
        whatsapp_chat_id="friend_chat_123"
    )

    repository.get_by_id.return_value = expected_contract

    service = ContractService(repository)

    result = service.get_contract(1)

    assert result.id == 1

    repository.get_by_id.assert_called_once_with(1)
    
def test_get_all_contracts():

    repository = Mock()

    repository.get_all.return_value = [
        Contract(
            id=1,
            name="Contract 1",
            total_amount=Decimal("100"),
            daily_amount=Decimal("10"),
            currency="USD",
            start_date=date.today(),
            whatsapp_chat_id="chat1"
        )
    ]

    service = ContractService(repository)

    result = service.get_all_contracts()

    assert len(result) == 1

    repository.get_all.assert_called_once()
    
def test_delete_contract():

    repository = Mock()

    contract = Contract(
        id=1,
        name="Friend Payment",
        total_amount=Decimal("2200"),
        daily_amount=Decimal("20"),
        currency="USD",
        start_date=date.today(),
        whatsapp_chat_id="friend_chat_123"
    )

    repository.get_by_id.return_value = contract

    service = ContractService(repository)

    result = service.delete_contract(1)

    assert result is True

    repository.delete.assert_called_once_with(contract)