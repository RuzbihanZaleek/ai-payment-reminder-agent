"""Integration-test harness.

These tests exercise the *real* stack -- FastAPI routers, dependency-injected
services, repositories and SQLAlchemy -- against an in-memory SQLite database.
Only the outside world (OpenAI, WhatsApp HTTP) is avoided; everything inside the
application boundary runs for real, so pagination, filtering, tenant isolation
and the standardized error envelope are verified through genuine HTTP calls.

The suite is DB-backed but uses SQLite (no Postgres needed), so it runs in the
sandbox as well as the container.
"""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 -- register every model on Base.metadata
from app.models.base import Base
from app.models.contract import Contract, ContractStatus
from app.models.payment import Payment
from app.models.agent_run import AgentRun
from app.models.scheduler_run import SchedulerRun
from app.enums.payment_status import PaymentStatus
from app.enums.approval_status import ApprovalStatus
from app.enums.payment_source import PaymentSource
from app.enums.agent_run_status import AgentRunStatus
from app.enums.scheduler_run_status import SchedulerRunStatus
from app.main import app


# Every module that opens its own session via ``SessionLocal()`` -- each imported
# the name directly, so each reference is patched to the test session factory.
_SESSION_MODULES = [
    "app.api.deps",
    "app.api.auth",
    "app.api.approval",
    "app.api.dashboard",
    "app.api.analytics",
    "app.api.reports.contracts",
    "app.api.reports.agent_runs",
    "app.api.reports.scheduler_runs",
    "app.api.health",
]


@pytest.fixture
def db_factory(monkeypatch):
    """A fresh in-memory SQLite database wired into the app for one test."""

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False
    )

    import importlib

    for module_path in _SESSION_MODULES:
        module = importlib.import_module(module_path)
        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal, raising=False)

    yield TestingSessionLocal

    Base.metadata.drop_all(engine)


@pytest.fixture
def client(db_factory):
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class ApiActor:
    """A registered+logged-in user with an auth header and DB seeding helpers."""

    def __init__(self, client: TestClient, session_factory, user_id: int, token: str):
        self.client = client
        self._session_factory = session_factory
        self.user_id = user_id
        self.headers = {"Authorization": f"Bearer {token}"}

    def create_contract(
        self,
        reference_code: str,
        total_amount: Decimal = Decimal("1000"),
        status: ContractStatus = ContractStatus.ACTIVE,
        whatsapp_chat_id: str = "chat",
    ) -> int:
        session = self._session_factory()
        try:
            contract = Contract(
                user_id=self.user_id,
                reference_code=reference_code,
                name="Integration Contract",
                total_amount=total_amount,
                daily_amount=Decimal("10"),
                currency="USD",
                start_date=date.today(),
                status=status,
                whatsapp_chat_id=whatsapp_chat_id,
            )
            session.add(contract)
            session.commit()
            session.refresh(contract)
            return contract.id
        finally:
            session.close()

    def add_payment(
        self,
        contract_id: int,
        amount: Decimal,
        status: PaymentStatus = PaymentStatus.APPROVED,
        approval_status: ApprovalStatus = ApprovalStatus.APPROVED,
        requires_manual_review: bool = False,
        payment_date: date | None = None,
    ) -> int:
        session = self._session_factory()
        try:
            payment = Payment(
                contract_id=contract_id,
                amount=amount,
                payment_date=payment_date or date.today(),
                status=status,
                approval_status=approval_status,
                requires_manual_review=requires_manual_review,
                source=PaymentSource.MANUAL,
            )
            session.add(payment)
            session.commit()
            session.refresh(payment)
            return payment.id
        finally:
            session.close()

    def add_agent_run(
        self,
        contract_id: int,
        status: AgentRunStatus = AgentRunStatus.COMPLETED,
    ) -> int:
        session = self._session_factory()
        try:
            run = AgentRun(
                contract_id=contract_id,
                message_id=f"msg-{contract_id}-{status.value}",
                status=status,
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            return run.id
        finally:
            session.close()


@pytest.fixture
def make_actor(client, db_factory):
    """Factory: register + log in a user and return an :class:`ApiActor`."""

    counter = {"n": 0}

    def _make(password: str = "password123") -> ApiActor:
        counter["n"] += 1
        email = f"user{counter['n']}@example.com"

        register = client.post(
            "/auth/register", json={"email": email, "password": password}
        )
        assert register.status_code == 201, register.text
        user_id = register.json()["id"]

        login = client.post(
            "/auth/login", json={"email": email, "password": password}
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]

        return ApiActor(client, db_factory, user_id, token)

    return _make


@pytest.fixture
def seed_scheduler_run():
    """Insert a scheduler run (global, not user-scoped) into the test DB."""

    def _seed(session_factory, status: SchedulerRunStatus = SchedulerRunStatus.COMPLETED):
        session = session_factory()
        try:
            run = SchedulerRun(run_type="daily_reminders", status=status)
            session.add(run)
            session.commit()
            session.refresh(run)
            return run.id
        finally:
            session.close()

    return _seed
