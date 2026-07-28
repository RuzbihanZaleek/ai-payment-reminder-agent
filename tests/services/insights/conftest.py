"""SQLite-backed harness for insight services (real services + real data)."""

from datetime import date, timedelta
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
from app.enums.payment_status import PaymentStatus
from app.enums.approval_status import ApprovalStatus
from app.enums.payment_source import PaymentSource

from app.repositories.contract_repository import ContractRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.scheduler_run_repository import SchedulerRunRepository
from app.repositories.scheduler_event_repository import SchedulerEventRepository
from app.services.contract_service import ContractService
from app.services.payment_service import PaymentService
from app.services.contract_reporting_service import ContractReportingService
from app.services.scheduler_reporting_service import SchedulerReportingService
from app.services.insights import (
    FinancialInsightService,
    ContractInsightService,
    PaymentInsightService,
    SchedulerInsightService,
)
from app.services.insights.recommendation_service import RecommendationService


class InsightHarness:
    def __init__(self, session):
        self.session = session
        self._user_seq = 0
        contract_repo = ContractRepository(session)
        payment_repo = PaymentRepository(session)
        self.contract_service = ContractService(contract_repo)
        self.payment_service = PaymentService(payment_repo)
        contract_reporting = ContractReportingService(
            self.contract_service, self.payment_service
        )
        scheduler_reporting = SchedulerReportingService(
            SchedulerRunRepository(session), SchedulerEventRepository(session)
        )

        self.financial = FinancialInsightService(
            self.contract_service, self.payment_service, contract_reporting
        )
        self.contracts = ContractInsightService(self.contract_service, self.payment_service)
        self.payments = PaymentInsightService(self.payment_service, self.contract_service)
        self.scheduler = SchedulerInsightService(scheduler_reporting)
        self.recommendations = RecommendationService(
            self.financial, self.contracts, self.payments
        )

    def user(self) -> int:
        self._user_seq += 1
        u = User(email=f"user{self._user_seq}@ex.com", hashed_password="x")
        self.session.add(u)
        self.session.commit()
        self.session.refresh(u)
        return u.id

    def contract(self, user_id, ref, total="1000", daily="10", name=None,
                 status=ContractStatus.ACTIVE, start_days_ago=0):
        c = Contract(
            user_id=user_id,
            reference_code=ref,
            name=name or f"{ref} Holder",
            total_amount=Decimal(total),
            daily_amount=Decimal(daily),
            currency="USD",
            start_date=date.today() - timedelta(days=start_days_ago),
            status=status,
            whatsapp_chat_id=f"chat-{ref}",
        )
        self.session.add(c)
        self.session.commit()
        self.session.refresh(c)
        return c

    def payment(self, contract_id, amount, days_ago=0,
                status=PaymentStatus.APPROVED, approval=ApprovalStatus.APPROVED):
        p = Payment(
            contract_id=contract_id,
            amount=Decimal(amount),
            payment_date=date.today() - timedelta(days=days_ago),
            status=status,
            approval_status=approval,
            source=PaymentSource.MANUAL,
        )
        self.session.add(p)
        self.session.commit()
        self.session.refresh(p)
        return p


@pytest.fixture
def harness():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield InsightHarness(session)
    finally:
        session.close()
        Base.metadata.drop_all(engine)
