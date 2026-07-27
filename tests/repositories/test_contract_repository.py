import uuid
from datetime import date
from decimal import Decimal

from app.models.contract import Contract, ContractStatus
from app.repositories.contract_repository import ContractRepository


def _ref() -> str:
    # reference_code is UNIQUE and db_session doesn't roll back -> unique per run.
    return f"INV-{uuid.uuid4().hex[:12]}"


def test_create_contract(db_session):

    repository = ContractRepository(db_session)

    contract = Contract(
        reference_code=_ref(),
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


def test_get_active_by_whatsapp_chat_id_returns_multiple(db_session):

    repository = ContractRepository(db_session)

    chat_id = f"chat_{uuid.uuid4().hex}"

    c1 = repository.create(
        Contract(
            reference_code=_ref(),
            name="Invoice 1",
            total_amount=Decimal("1100"),
            daily_amount=Decimal("10"),
            currency="USD",
            start_date=date.today(),
            whatsapp_chat_id=chat_id,
            status=ContractStatus.ACTIVE,
        )
    )
    c2 = repository.create(
        Contract(
            reference_code=_ref(),
            name="Invoice 2",
            total_amount=Decimal("1100"),
            daily_amount=Decimal("10"),
            currency="USD",
            start_date=date.today(),
            whatsapp_chat_id=chat_id,
            status=ContractStatus.ACTIVE,
        )
    )
    # A closed contract for the same chat must be excluded.
    repository.create(
        Contract(
            reference_code=_ref(),
            name="Closed",
            total_amount=Decimal("1100"),
            daily_amount=Decimal("10"),
            currency="USD",
            start_date=date.today(),
            whatsapp_chat_id=chat_id,
            status=ContractStatus.COMPLETED,
        )
    )

    active = repository.get_active_by_whatsapp_chat_id(chat_id)

    active_ids = {c.id for c in active}
    assert active_ids == {c1.id, c2.id}