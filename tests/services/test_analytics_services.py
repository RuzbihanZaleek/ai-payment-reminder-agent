from decimal import Decimal

from app.services.contract_analytics_service import ContractAnalyticsService
from app.services.payment_analytics_service import PaymentAnalyticsService
from app.services.agent_analytics_service import AgentAnalyticsService
from app.services.reminder_analytics_service import ReminderAnalyticsService
from app.services.analytics_service import AnalyticsService


class _Reporting:
    def __init__(self, method_name, value):
        setattr(self, method_name, lambda: value)


# --- Contract analytics -----------------------------------------------------

def test_contract_analytics_derives_collected_and_rate():

    reporting = _Reporting("get_contract_stats", {
        "total_contracts": 3,
        "total_contract_value": Decimal("1000"),
        "active_contracts": 2,
        "completed_contracts": 1,
        "total_remaining_amount": Decimal("400"),
    })

    result = ContractAnalyticsService(reporting).get_contract_analytics()

    assert result["total_contract_value"] == Decimal("1000")
    assert result["total_outstanding_amount"] == Decimal("400")
    assert result["total_collected_amount"] == Decimal("600")
    assert result["collection_rate"] == 0.6


def test_contract_analytics_zero_value_rate_is_zero():

    reporting = _Reporting("get_contract_stats", {
        "total_contract_value": Decimal("0"),
        "total_remaining_amount": Decimal("0"),
    })

    result = ContractAnalyticsService(reporting).get_contract_analytics()

    assert result["collection_rate"] == 0.0


# --- Payment analytics ------------------------------------------------------

def test_payment_analytics_average():

    reporting = _Reporting("get_payment_stats", {
        "payment_transaction_count": 4,
        "total_amount_received": Decimal("200"),
        "pending_review_count": 1,
        "pending_review_amount": Decimal("25"),
    })

    result = PaymentAnalyticsService(reporting).get_payment_analytics()

    assert result["total_amount_received"] == Decimal("200")
    assert result["payment_transaction_count"] == 4
    assert result["average_payment_amount"] == Decimal("50")
    assert result["pending_review_amount"] == Decimal("25")


def test_payment_analytics_zero_transactions():

    reporting = _Reporting("get_payment_stats", {
        "payment_transaction_count": 0,
        "total_amount_received": Decimal("0"),
        "pending_review_amount": Decimal("0"),
    })

    result = PaymentAnalyticsService(reporting).get_payment_analytics()

    assert result["average_payment_amount"] == Decimal("0")


# --- Agent analytics --------------------------------------------------------

def test_agent_analytics_success_rate():

    reporting = _Reporting("get_agent_stats", {
        "total_agent_runs": 10,
        "completed_runs": 8,
        "failed_runs": 2,
    })

    result = AgentAnalyticsService(reporting).get_agent_analytics()

    assert result["success_rate"] == 0.8
    assert result["failed_runs"] == 2


# --- Reminder analytics -----------------------------------------------------

def test_reminder_analytics_delivery_rate():

    reminder_reporting = _Reporting("get_reminder_stats", {"total_reminders_logged": 12})
    scheduler_reporting = _Reporting("get_scheduler_stats", {
        "total_scheduler_runs": 5,
        "failed_scheduler_runs": 1,
        "total_reminders_sent": 9,
        "total_reminders_failed": 3,
    })

    result = ReminderAnalyticsService(
        reminder_reporting, scheduler_reporting
    ).get_reminder_analytics()

    assert result["total_reminders_logged"] == 12
    assert result["total_reminders_sent"] == 9
    assert result["total_reminders_failed"] == 3
    assert result["delivery_rate"] == 0.75


def test_reminder_analytics_no_attempts():

    reminder_reporting = _Reporting("get_reminder_stats", {"total_reminders_logged": 0})
    scheduler_reporting = _Reporting("get_scheduler_stats", {
        "total_reminders_sent": 0,
        "total_reminders_failed": 0,
    })

    result = ReminderAnalyticsService(
        reminder_reporting, scheduler_reporting
    ).get_reminder_analytics()

    assert result["delivery_rate"] == 0.0


# --- Composer ---------------------------------------------------------------

class _Analytics:
    def __init__(self, method_name, value):
        setattr(self, method_name, lambda: value)


def test_analytics_service_composes_sections():

    service = AnalyticsService(
        _Analytics("get_contract_analytics", {"total_contract_value": Decimal("1000")}),
        _Analytics("get_payment_analytics", {"payment_transaction_count": 4}),
        _Analytics("get_reminder_analytics", {"total_reminders_sent": 9}),
        _Analytics("get_agent_analytics", {"total_agent_runs": 10}),
    )

    overview = service.get_overview()

    assert overview["contracts"]["total_contract_value"] == Decimal("1000")
    assert overview["payments"]["payment_transaction_count"] == 4
    assert overview["reminders"]["total_reminders_sent"] == 9
    assert overview["agents"]["total_agent_runs"] == 10