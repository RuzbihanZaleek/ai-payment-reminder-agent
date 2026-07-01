from datetime import date
from decimal import Decimal

import pytest

from app.agents.reminder_engine import ReminderEngine


@pytest.fixture
def reminder_engine():

    return ReminderEngine()


def test_calculate_pending_amount(
    reminder_engine
):

    remaining = reminder_engine.calculate_pending_amount(
        Decimal("2200"),
        Decimal("920")
    )

    assert remaining == Decimal("1280")


def test_calculate_pending_days(
    reminder_engine
):

    days = reminder_engine.calculate_pending_days(
        Decimal("20"),
        Decimal("100")
    )

    assert days == 5


def test_scenario_one_three_days_pending(
    reminder_engine
):

    context = reminder_engine.build_reminder_context(
        last_covered_date=date(2026, 6, 17),
        today=date(2026, 6, 20),
        total_amount=Decimal("2200"),
        total_paid=Decimal("2140"),
        daily_amount=Decimal("20")
    )

    assert context["pending_amount"] == Decimal("60")

    assert context["pending_dates"] == [
        date(2026, 6, 18),
        date(2026, 6, 19),
        date(2026, 6, 20)
    ]


def test_scenario_two_friend_pays_multiple_days(
    reminder_engine
):

    # Contract:
    # Daily = $20
    #
    # Remaining before payment:
    # $100
    #
    # Friend pays:
    # $100
    #
    # Next reminder should start
    # after the covered days

    context = reminder_engine.build_reminder_context(
        last_covered_date=date(2026, 6, 20),
        today=date(2026, 6, 25),
        total_amount=Decimal("2200"),
        total_paid=Decimal("2100"),
        daily_amount=Decimal("20")
    )

    assert context["pending_amount"] == Decimal("100")

    assert context["pending_dates"] == [
        date(2026, 6, 21),
        date(2026, 6, 22),
        date(2026, 6, 23),
        date(2026, 6, 24),
        date(2026, 6, 25),
    ]


def test_invalid_daily_amount(
    reminder_engine
):

    with pytest.raises(ValueError):

        reminder_engine.calculate_pending_days(
            Decimal("0"),
            Decimal("100")
        )