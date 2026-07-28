"""FinancialMemoryService: store/retrieve, tenant isolation, dedup, audit (SQLite)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.base import Base
from app.models.user import User
from app.repositories.financial_memory_repository import FinancialMemoryRepository
from app.services.ai_memory import FinancialMemoryService, FinancialMemoryType


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def _user(session, email):
    u = User(email=email, hashed_password="x")
    session.add(u)
    session.commit()
    session.refresh(u)
    return u.id


class FakeAudit:
    AI_MEMORY_CREATED = "AI_MEMORY_CREATED"

    def __init__(self):
        self.records = []

    def record(self, **kwargs):
        self.records.append(kwargs)


def test_create_and_retrieve(session):
    user = _user(session, "a@ex.com")
    service = FinancialMemoryService(FinancialMemoryRepository(session))

    service.remember(user, FinancialMemoryType.USER_GOAL, "wants monthly summaries")

    memories = service.get_user_memories(user)
    assert len(memories) == 1
    assert memories[0].memory_type == "USER_GOAL"
    assert memories[0].content == "wants monthly summaries"


def test_get_by_type(session):
    user = _user(session, "a@ex.com")
    service = FinancialMemoryService(FinancialMemoryRepository(session))
    service.remember(user, FinancialMemoryType.USER_GOAL, "goal")
    service.remember(user, FinancialMemoryType.FINANCIAL_PATTERN, "late payers")

    goals = service.get_by_type(user, FinancialMemoryType.USER_GOAL)
    assert [m.content for m in goals] == ["goal"]


def test_dedup_identical_memory(session):
    user = _user(session, "a@ex.com")
    service = FinancialMemoryService(FinancialMemoryRepository(session))

    first = service.remember(user, FinancialMemoryType.USER_GOAL, "same")
    second = service.remember(user, FinancialMemoryType.USER_GOAL, "same")

    assert first is not None
    assert second is None  # duplicate skipped
    assert len(service.get_user_memories(user)) == 1


def test_tenant_isolation(session):
    owner = _user(session, "owner@ex.com")
    other = _user(session, "other@ex.com")
    service = FinancialMemoryService(FinancialMemoryRepository(session))

    service.remember(owner, FinancialMemoryType.USER_GOAL, "owner goal")
    service.remember(other, FinancialMemoryType.USER_GOAL, "other goal")

    assert [m.content for m in service.get_user_memories(owner)] == ["owner goal"]
    # Relevant-memories view is also user-scoped.
    assert service.get_relevant_memories(other) == [{"type": "USER_GOAL", "content": "other goal"}]


def test_audit_on_create(session):
    user = _user(session, "a@ex.com")
    audit = FakeAudit()
    service = FinancialMemoryService(FinancialMemoryRepository(session), audit_service=audit)

    service.remember(user, FinancialMemoryType.RISK_SIGNAL, "overdue risk")

    assert audit.records[0]["action"] == "AI_MEMORY_CREATED"
    assert audit.records[0]["metadata"]["memory_type"] == "RISK_SIGNAL"
