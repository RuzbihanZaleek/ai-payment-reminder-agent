from decimal import Decimal

from app.services.contract_reporting_service import ContractReportingService
from app.services.payment_reporting_service import PaymentReportingService
from app.services.receipt_reporting_service import ReceiptReportingService
from app.services.agent_reporting_service import AgentReportingService
from app.services.scheduler_reporting_service import SchedulerReportingService


class FakeContract:

    def __init__(self):
        self.id = 1
        self.reference_code = "INV001"
        self.name = "Friend Payment"
        self.total_amount = Decimal("1000")


class FakeContractService:

    def __init__(self, contract):
        self.contract = contract

    def get_contract(self, contract_id):

        return self.contract


class FakePaymentService:

    def __init__(self, payments, total_paid=Decimal("0"), remaining=Decimal("0")):
        self.payments = payments
        self._total_paid = total_paid
        self._remaining = remaining

    def get_contract_payments(self, contract_id):
        return self.payments

    def calculate_total_paid(self, contract_id):
        return self._total_paid

    def calculate_remaining_amount(self, total_amount, contract_id):
        return self._remaining


def test_contract_summary():

    service = ContractReportingService(
        FakeContractService(FakeContract()),
        FakePaymentService(
            payments=[object(), object(), object()],
            total_paid=Decimal("120"),
            remaining=Decimal("880"),
        ),
    )

    summary = service.get_contract_summary(1)

    assert summary["contract_id"] == 1
    assert summary["reference_code"] == "INV001"
    assert summary["total_paid"] == Decimal("120")
    assert summary["remaining_amount"] == Decimal("880")
    assert summary["payment_count"] == 3


def test_contract_summary_missing_returns_none():

    service = ContractReportingService(
        FakeContractService(None),
        FakePaymentService(payments=[]),
    )

    assert service.get_contract_summary(999) is None


def test_payment_history():

    payments = [object(), object()]
    service = PaymentReportingService(FakePaymentService(payments=payments))

    assert service.get_payment_history(1) == payments


class FakeReceiptRepository:

    def __init__(self, receipts):
        self.receipts = receipts

    def get_by_contract_id(self, contract_id):
        return self.receipts


def test_receipt_history():

    receipts = [object()]
    service = ReceiptReportingService(FakeReceiptRepository(receipts))

    assert service.get_receipt_history(1) == receipts


class FakeAgentRunRepository:

    def __init__(self, run=None, recent=None):
        self.run = run
        self.recent = recent or []

    def get_recent(self, limit):
        return self.recent

    def get_by_id(self, run_id):
        return self.run


class FakeAgentEventRepository:

    def __init__(self, events):
        self.events = events

    def get_by_run_id(self, run_id):
        return self.events


def test_agent_run_details():

    run = object()
    events = [object(), object()]

    service = AgentReportingService(
        FakeAgentRunRepository(run=run),
        FakeAgentEventRepository(events),
    )

    details = service.get_run_details(5)

    assert details["run"] is run
    assert details["events"] == events


def test_agent_run_details_missing_returns_none():

    service = AgentReportingService(
        FakeAgentRunRepository(run=None),
        FakeAgentEventRepository([]),
    )

    assert service.get_run_details(999) is None


class FakeSchedulerRunRepository:

    def __init__(self, run=None, recent=None):
        self.run = run
        self.recent = recent or []

    def get_recent(self, limit):
        return self.recent

    def get_by_id(self, run_id):
        return self.run


class FakeSchedulerEventRepository:

    def __init__(self, events):
        self.events = events

    def get_by_run_id(self, run_id):
        return self.events


def test_scheduler_details():

    run = object()
    events = [object()]

    service = SchedulerReportingService(
        FakeSchedulerRunRepository(run=run),
        FakeSchedulerEventRepository(events),
    )

    details = service.get_run_details(3)

    assert details["run"] is run
    assert details["events"] == events


def test_scheduler_details_missing_returns_none():

    service = SchedulerReportingService(
        FakeSchedulerRunRepository(run=None),
        FakeSchedulerEventRepository([]),
    )

    assert service.get_run_details(999) is None