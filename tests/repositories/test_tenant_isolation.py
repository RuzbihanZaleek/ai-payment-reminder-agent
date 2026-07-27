"""Tenant-isolation tests (Phase 10.2).

These verify that the user-scoped repository queries never leak another user's
data. They exercise the real database, so they run in the container/CI (Postgres)
rather than the sandbox.
"""

import uuid
from datetime import date
from decimal import Decimal

from app.models.user import User
from app.models.contract import Contract, ContractStatus
from app.models.payment import Payment
from app.enums.payment_status import PaymentStatus
from app.enums.payment_source import PaymentSource
from app.repositories.user_repository import UserRepository
from app.repositories.contract_repository import ContractRepository
from app.repositories.payment_repository import PaymentRepository


def _ref() -> str:
    # reference_code is UNIQUE and db_session doesn't roll back -> unique per run.
    return f"INV-{uuid.uuid4().hex[:12]}"


def _make_user(db) -> User:
    return UserRepository(db).create(
        User(
            email=f"user-{uuid.uuid4().hex}@example.com",
            hashed_password="x",
        )
    )


def _make_contract(db, user_id) -> Contract:
    return ContractRepository(db).create(
        Contract(
            user_id=user_id,
            reference_code=_ref(),
            name="Contract",
            total_amount=Decimal("1000"),
            daily_amount=Decimal("10"),
            currency="USD",
            start_date=date.today(),
            whatsapp_chat_id=f"chat_{uuid.uuid4().hex}",
            status=ContractStatus.ACTIVE,
        )
    )


def test_contracts_scoped_to_owner(db_session):

    owner = _make_user(db_session)
    other = _make_user(db_session)

    mine = _make_contract(db_session, owner.id)
    _make_contract(db_session, other.id)

    repository = ContractRepository(db_session)

    owned = repository.get_all_for_user(owner.id)

    owned_ids = {c.id for c in owned}
    assert mine.id in owned_ids
    # No contract belonging to another user leaks through.
    assert all(c.user_id == owner.id for c in owned)


def test_get_by_id_for_user_rejects_other_owner(db_session):

    owner = _make_user(db_session)
    other = _make_user(db_session)

    contract = _make_contract(db_session, owner.id)

    repository = ContractRepository(db_session)

    # Owner can read it; another user gets nothing.
    assert repository.get_by_id_for_user(contract.id, owner.id) is not None
    assert repository.get_by_id_for_user(contract.id, other.id) is None


def test_payments_scoped_to_contract_owner(db_session):

    owner = _make_user(db_session)
    other = _make_user(db_session)

    owner_contract = _make_contract(db_session, owner.id)
    other_contract = _make_contract(db_session, other.id)

    payment_repository = PaymentRepository(db_session)

    payment_repository.create(
        Payment(
            contract_id=owner_contract.id,
            amount=Decimal("20.00"),
            payment_date=date.today(),
            status=PaymentStatus.APPROVED,
            source=PaymentSource.MANUAL,
        )
    )
    payment_repository.create(
        Payment(
            contract_id=other_contract.id,
            amount=Decimal("99.00"),
            payment_date=date.today(),
            status=PaymentStatus.APPROVED,
            source=PaymentSource.MANUAL,
        )
    )

    owner_payments = payment_repository.get_all_for_user(owner.id)

    owner_contract_ids = {owner_contract.id}
    assert all(p.contract_id in owner_contract_ids for p in owner_payments)
    # The other user's $99 payment must not appear.
    assert all(p.amount != Decimal("99.00") for p in owner_payments)