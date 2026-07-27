from decimal import Decimal

from app.services.reminder_policy_service import ReminderPolicyService


class FakeContract:

    def __init__(self, contract_id=1, total_amount=Decimal("1000")):
        self.id = contract_id
        self.total_amount = total_amount


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
