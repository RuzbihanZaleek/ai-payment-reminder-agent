from datetime import date, timedelta
from decimal import Decimal

from app.models.contract import ContractStatus
from app.services.reminder_policy_service import ReminderPolicyService


class FakeContract:

    def __init__(
        self,
        contract_id=1,
        total_amount=Decimal("1000"),
        status=ContractStatus.ACTIVE,
        start_date=None,
    ):
        self.id = contract_id
        self.total_amount = total_amount
        self.status = status
        # Default to a contract that has already started (yesterday).
        self.start_date = start_date or (date.today() - timedelta(days=1))


class FakePaymentService:

    def __init__(self, remaining):
        self.remaining = remaining

    def calculate_remaining_amount(self, total_amount, contract_id):

        return self.remaining


class FakePaymentRepository:

    def __init__(self, paid_today=False):
        self.paid_today = paid_today

    def has_payment_for_date(self, contract_id, payment_date):

        return self.paid_today


class FakeReminderLogRepository:

    def __init__(self, reminded_today=False):
        self.reminded_today = reminded_today

    def has_sent_today(self, contract_id):

        return self.reminded_today


def _policy(remaining, paid_today=False, reminded_today=False):

    return ReminderPolicyService(
        FakePaymentService(remaining),
        FakePaymentRepository(paid_today=paid_today),
        FakeReminderLogRepository(reminded_today=reminded_today),
    )


def test_completed_contract_is_not_reminded():

    # Nothing owed -> no reminder.
    policy = _policy(remaining=Decimal("0"))

    assert policy.should_send_reminder(FakeContract()) is False


def test_payment_today_suppresses_reminder():

    policy = _policy(remaining=Decimal("500"), paid_today=True)

    assert policy.should_send_reminder(FakeContract()) is False


def test_already_reminded_today_suppresses_reminder():

    policy = _policy(
        remaining=Decimal("500"),
        paid_today=False,
        reminded_today=True,
    )

    assert policy.should_send_reminder(FakeContract()) is False


def test_eligible_reminder_returns_true():

    policy = _policy(
        remaining=Decimal("500"),
        paid_today=False,
        reminded_today=False,
    )

    assert policy.should_send_reminder(FakeContract()) is True


def test_inactive_contract_is_not_reminded():

    # A contract that is owed money but not ACTIVE must never be reminded.
    policy = _policy(remaining=Decimal("500"))

    for status in (
        ContractStatus.PAUSED,
        ContractStatus.CANCELLED,
        ContractStatus.COMPLETED,
    ):
        contract = FakeContract(status=status)

        assert policy.should_send_reminder(contract) is False


def test_not_yet_started_contract_is_not_reminded():

    # An active contract whose start date is in the future is not due yet.
    policy = _policy(remaining=Decimal("500"))

    contract = FakeContract(start_date=date.today() + timedelta(days=1))

    assert policy.should_send_reminder(contract) is False
