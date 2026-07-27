from decimal import Decimal

from app.services.contract_reporting_service import ContractReportingService
from app.services.payment_reporting_service import PaymentReportingService
from app.services.receipt_reporting_service import ReceiptReportingService
from app.services.agent_reporting_service import AgentReportingService
from app.services.scheduler_reporting_service import SchedulerReportingService
from app.repositories.pagination import PageResult
from app.repositories.filters import PaymentFilter
from app.enums.sort_order import SortOrder


class FakeContract:

    def __init__(self, user_id=7):
        self.id = 1
        self.user_id = user_id
        self.reference_code = "INV001"
        self.name = "Friend Payment"
        self.total_amount = Decimal("1000")


class FakeContractService:

    def __init__(self, contract, contracts=None):
        self.contract = contract
        self.contracts = contracts or ([] if contract is None else [contract])

    def get_contract(self, contract_id):

        return self.contract

    def get_user_contracts(self, user_id):

        return self.contracts


class FakePaymentService:

    def __init__(self, payments, total_paid=Decimal("0"), remaining=Decimal("0")):
        self.payments = payments
        self._total_paid = total_paid
        self._remaining = remaining

    def get_contract_payments(self, contract_id):
        return self.payments

    def get_contract_payments_page(self, contract_id, payment_filter, page, page_size, order):
        return PageResult(items=self.payments, total=len(self.payments))

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

    summary = service.get_contract_summary(1, 7)

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

    assert service.get_contract_summary(999, 7) is None


def test_contract_summary_other_user_returns_none():
    # Tenant isolation: contract owned by user 7, requested by user 99.
    service = ContractReportingService(
        FakeContractService(FakeContract(user_id=7)),
        FakePaymentService(payments=[]),
    )

    assert service.get_contract_summary(1, 99) is None


def test_payment_history():

    payments = [object(), object()]
    service = PaymentReportingService(FakePaymentService(payments=payments))

    result = service.get_payment_history(
        1, PaymentFilter(), page=1, page_size=20, order=SortOrder.DESC
    )

    assert result.items == payments
    assert result.total == 2


class FakeReceiptRepository:

    def __init__(self, receipts):
        self.receipts = receipts

    def get_by_contract_id(self, contract_id):
        return self.receipts

    def get_by_contract_id_page(self, contract_id, page, page_size, order):
        return PageResult(items=self.receipts, total=len(self.receipts))


def test_receipt_history():

    receipts = [object()]
    service = ReceiptReportingService(FakeReceiptRepository(receipts))

    result = service.get_receipt_history(1, page=1, page_size=20, order=SortOrder.DESC)

    assert result.items == receipts
    assert result.total == 1


class FakeAgentRunRepository:

    def __init__(self, run=None, recent=None):
        self.run = run
        self.recent = recent or []

    def get_recent(self, limit):
        return self.recent

    def get_by_id(self, run_id):
        return self.run

    def get_recent_for_user(self, user_id, limit):
        return self.recent

    def get_by_id_for_user(self, run_id, user_id):
        return self.run

    def get_all_for_user(self, user_id):
        return self.recent


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

    details = service.get_run_details(5, 7)

    assert details["run"] is run
    assert details["events"] == events


def test_agent_run_details_missing_returns_none():

    service = AgentReportingService(
        FakeAgentRunRepository(run=None),
        FakeAgentEventRepository([]),
    )

    assert service.get_run_details(999, 7) is None


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

# --- Phase 9.1.1 refinements -------------------------------------------------

class _Payment:
    def __init__(self, amount):
        self.amount = amount


class FakePaymentServiceStats:
    def __init__(self, payments, total_received, pending_count, pending_amount):
        self.payments = payments
        self.total_received = total_received
        self.pending_count = pending_count
        self.pending_amount = pending_amount

    def get_user_payments(self, user_id):
        return self.payments

    def calculate_total_received_for_user(self, user_id):
        return self.total_received

    def count_pending_reviews_for_user(self, user_id):
        return self.pending_count

    def calculate_pending_review_amount_for_user(self, user_id):
        return self.pending_amount


def test_payment_stats_transaction_count_and_confirmed_total():

    service = PaymentReportingService(
        FakePaymentServiceStats(
            payments=[_Payment(Decimal("20")), _Payment(Decimal("30")), _Payment(Decimal("10"))],
            total_received=Decimal("40"),
            pending_count=2,
            pending_amount=Decimal("50"),
        )
    )

    stats = service.get_payment_stats(7)

    assert stats["payment_transaction_count"] == 3
    # Confirmed money only, not the sum of all transactions.
    assert stats["total_amount_received"] == Decimal("40")
    assert stats["pending_review_count"] == 2
    assert stats["pending_review_amount"] == Decimal("50")


class _Run:
    def __init__(self, status, successful_count, failed_count):
        self.status = status
        self.successful_count = successful_count
        self.failed_count = failed_count


class FakeSchedulerRunRepoStats:
    def __init__(self, runs):
        self.runs = runs

    def get_all(self):
        return self.runs


def test_scheduler_stats_runs_and_reminder_deliveries():

    from app.enums.scheduler_run_status import SchedulerRunStatus

    runs = [
        _Run(SchedulerRunStatus.COMPLETED, 3, 1),
        _Run(SchedulerRunStatus.FAILED, 0, 0),
        _Run(SchedulerRunStatus.COMPLETED, 2, 1),
    ]

    service = SchedulerReportingService(FakeSchedulerRunRepoStats(runs), None)

    stats = service.get_scheduler_stats()

    assert stats["total_scheduler_runs"] == 3
    assert stats["failed_scheduler_runs"] == 1
    assert stats["total_reminders_sent"] == 5
    assert stats["total_reminders_failed"] == 2


class _ApprovalPayment:
    def __init__(self, amount, approval_status, requires_manual_review):
        self.amount = amount
        self.approval_status = approval_status
        self.requires_manual_review = requires_manual_review


class FakePaymentRepoApproval:
    def __init__(self, payments):
        self.payments = payments

    def get_by_approval_status(self, status):
        return [p for p in self.payments if p.approval_status == status]


def _payment_service_with(payments):
    from app.services.payment_service import PaymentService

    return PaymentService(FakePaymentRepoApproval(payments))


def test_pending_review_counts_only_manual_review():

    from app.enums.approval_status import ApprovalStatus

    service = _payment_service_with([
        _ApprovalPayment(Decimal("20"), ApprovalStatus.PENDING, True),
        _ApprovalPayment(Decimal("30"), ApprovalStatus.PENDING, False),
        _ApprovalPayment(Decimal("15"), ApprovalStatus.PENDING, True),
    ])

    assert service.count_pending_approvals() == 2


def test_pending_review_amount_sums_only_manual_review():

    from app.enums.approval_status import ApprovalStatus

    service = _payment_service_with([
        _ApprovalPayment(Decimal("20"), ApprovalStatus.PENDING, True),
        _ApprovalPayment(Decimal("30"), ApprovalStatus.PENDING, False),
        _ApprovalPayment(Decimal("15"), ApprovalStatus.PENDING, True),
    ])

    assert service.calculate_pending_review_amount() == Decimal("35")


def test_total_received_includes_only_approved():

    from app.enums.approval_status import ApprovalStatus

    service = _payment_service_with([
        _ApprovalPayment(Decimal("40"), ApprovalStatus.APPROVED, False),
        _ApprovalPayment(Decimal("30"), ApprovalStatus.PENDING, False),   # excluded
        _ApprovalPayment(Decimal("25"), ApprovalStatus.APPROVED, False),
        _ApprovalPayment(Decimal("10"), ApprovalStatus.REJECTED, False),  # excluded
    ])

    assert service.calculate_total_received() == Decimal("65")
