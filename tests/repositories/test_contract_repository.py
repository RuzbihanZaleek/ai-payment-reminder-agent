from datetime import date
from decimal import Decimal

from app.models.contract import Contract
from app.repositories.contract_repository import ContractRepository


def test_create_contract(db_session):

    repository = ContractRepository(db_session)

    contract = Contract(
        name="Friend Payment",
        total_amount=Decimal("2200"),
        daily_amount=Decimal("20"),
        currency="USD",
        start_date=date.today(),
        whatsapp_chat_id="friend_chat_123"
    )

    saved_contract = repository.create(contract)

    assert saved_contract.id is not None
    assert saved_contract.name == "Friend Payment"