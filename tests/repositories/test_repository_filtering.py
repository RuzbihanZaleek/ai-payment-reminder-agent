"""Repository-layer pagination / filtering / ordering (SQLite-backed unit test).

These live at the repository layer because that is where pagination, filtering
and sorting are owned. SQLite keeps them runnable without Postgres.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 -- register models
from app.models.base import Base
from app.models.user import User
from app.models.contract import Contract, ContractStatus
from app.models.payment import Payment
from app.models.agent_run import AgentRun
from app.models.scheduler_run import SchedulerRun
from app.enums.payment_status import PaymentStatus
from app.enums.approval_status import ApprovalStatus
from app.enums.payment_source import PaymentSource
from app.enums.agent_run_status import AgentRunStatus
from app.enums.scheduler_run_status import SchedulerRunStatus
from app.enums.sort_order import SortOrder
from app.repositories.filters import (
    PaymentFilter,
    AgentRunFilter,
    SchedulerRunFilter,
)
from app.repositories.contract_repository import ContractRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.scheduler_run_repository import SchedulerRunRepository


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def _user(session) -> int:
    user = User(email="u@example.com", hashed_password="x")
    session.add(user)
    session.commit()
    return user.id


def _contract(session, user_id, code, status=ContractStatus.ACTIVE) -> Contract:
    contract = Contract(
        user_id=user_id,
        reference_code=code,
        name="C",
        total_amount=Decimal("1000"),
        daily_amount=Decimal("10"),
        currency="USD",
        start_date=date.today(),
        status=status,
        whatsapp_chat_id="chat",
    )
    session.add(contract)
    session.commit()
    return contract


def _payment(session, contract_id, amount, status=PaymentStatus.APPROVED,
             approval=ApprovalStatus.APPROVED, payment_date=None):
    payment = Payment(
        contract_id=contract_id,
        amount=Decimal(amount),
        payment_date=payment_date or date.today(),
        status=status,
        approval_status=approval,
        source=PaymentSource.MANUAL,
    )
    session.add(payment)
    session.commit()
    return payment


def test_contract_status_filter(session):
    user_id = _user(session)
    _contract(session, user_id, "ACT", ContractStatus.ACTIVE)
    _contract(session, user_id, "DONE", ContractStatus.COMPLETED)

    repo = ContractRepository(session)

    assert len(repo.get_all_for_user(user_id)) == 2
    active = repo.get_all_for_user(user_id, ContractStatus.ACTIVE)
    assert len(active) == 1
    assert active[0].reference_code == "ACT"


def test_payment_page_filter_and_pagination(session):
    user_id = _user(session)
    contract = _contract(session, user_id, "P1")

    for i in range(1, 6):
        _payment(session, contract.id, i)

    repo = PaymentRepository(session)

    page = repo.get_by_contract_id_page(
        contract.id, PaymentFilter(), page=1, page_size=2, order=SortOrder.ASC
    )
    assert page.total == 5
    assert len(page.items) == 2
    assert page.items[0].amount == Decimal("1")

    filtered = repo.get_by_contract_id_page(
        contract.id,
        PaymentFilter(min_amount=Decimal("3")),
        page=1,
        page_size=10,
        order=SortOrder.ASC,
    )
    assert filtered.total == 3


def test_payment_page_ordering(session):
    user_id = _user(session)
    contract = _contract(session, user_id, "P2")

    p1 = _payment(session, contract.id, 10)
    p2 = _payment(session, contract.id, 20)

    repo = PaymentRepository(session)

    desc = repo.get_by_contract_id_page(
        contract.id, PaymentFilter(), page=1, page_size=10, order=SortOrder.DESC
    )
    assert [p.id for p in desc.items] == [p2.id, p1.id]


def test_approval_status_for_user_page_scopes_by_owner(session):
    owner_id = _user(session)
    other = User(email="other@example.com", hashed_password="x")
    session.add(other)
    session.commit()

    owned = _contract(session, owner_id, "OWN")
    foreign = _contract(session, other.id, "FOREIGN")

    _payment(session, owned.id, 10, PaymentStatus.PENDING, ApprovalStatus.PENDING)
    _payment(session, foreign.id, 99, PaymentStatus.PENDING, ApprovalStatus.PENDING)

    repo = PaymentRepository(session)

    page = repo.get_by_approval_status_for_user_page(
        owner_id, ApprovalStatus.PENDING, page=1, page_size=10, order=SortOrder.DESC
    )

    assert page.total == 1
    assert page.items[0].amount == Decimal("10")


def test_agent_run_status_and_date_filter(session):
    user_id = _user(session)
    contract = _contract(session, user_id, "AR")

    for status in (AgentRunStatus.COMPLETED, AgentRunStatus.COMPLETED, AgentRunStatus.FAILED):
        session.add(AgentRun(contract_id=contract.id, message_id=f"m{status.value}", status=status))
    session.commit()

    repo = AgentRunRepository(session)

    completed = repo.get_for_user_page(
        user_id, AgentRunFilter(status=AgentRunStatus.COMPLETED),
        page=1, page_size=10, order=SortOrder.DESC,
    )
    assert completed.total == 2


def test_scheduler_run_status_filter(session):
    session.add(SchedulerRun(run_type="daily", status=SchedulerRunStatus.COMPLETED))
    session.add(SchedulerRun(run_type="daily", status=SchedulerRunStatus.FAILED))
    session.commit()

    repo = SchedulerRunRepository(session)

    failed = repo.get_page(
        SchedulerRunFilter(status=SchedulerRunStatus.FAILED),
        page=1, page_size=10, order=SortOrder.DESC,
    )
    assert failed.total == 1
