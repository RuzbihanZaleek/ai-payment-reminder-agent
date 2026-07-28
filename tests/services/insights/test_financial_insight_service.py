from decimal import Decimal


def test_financial_summary_totals_and_collection_rate(harness):
    user = harness.user()
    c1 = harness.contract(user, "INV001", total="1000", daily="10")
    c2 = harness.contract(user, "INV002", total="1000", daily="20")
    harness.payment(c1.id, "200")   # APPROVED (status) -> counts toward collected
    harness.payment(c2.id, "300")

    summary = harness.financial.get_financial_summary(user)

    assert summary["active_contracts"] == 2
    assert summary["total_active_capital"] == Decimal("2000")
    assert summary["total_expected_return"] == Decimal("2000")
    assert summary["total_collected"] == Decimal("500")
    assert summary["total_outstanding"] == Decimal("1500")
    assert summary["collection_rate"] == 0.25  # 500 / 2000
    assert summary["daily_expected_income"] == Decimal("30")
    assert summary["monthly_expected_income"] == Decimal("900")


def test_only_approved_payments_count_as_collected(harness):
    user = harness.user()
    c = harness.contract(user, "INV001", total="1000")
    harness.payment(c.id, "100")  # approved
    # A pending (manual-review) payment must NOT count as collected.
    from app.enums.payment_status import PaymentStatus
    from app.enums.approval_status import ApprovalStatus
    harness.payment(c.id, "500", status=PaymentStatus.PENDING, approval=ApprovalStatus.PENDING)

    assert harness.financial.get_total_collected(user) == Decimal("100")
    assert harness.financial.get_total_outstanding(user) == Decimal("900")


def test_expected_next_month_income_capped_by_remaining(harness):
    user = harness.user()
    # daily 20 -> month 600, but only 100 remains -> capped at 100.
    c = harness.contract(user, "INV001", total="1000", daily="20")
    harness.payment(c.id, "900")

    assert harness.financial.get_expected_next_month_income(user) == Decimal("100")


def test_empty_portfolio(harness):
    user = harness.user()

    summary = harness.financial.get_financial_summary(user)

    assert summary["total_active_capital"] == Decimal("0")
    assert summary["total_collected"] == Decimal("0")
    assert summary["collection_rate"] == 0.0


def test_tenant_isolation(harness):
    owner = harness.user()
    other = harness.user()
    harness.contract(owner, "INV001", total="1000")
    harness.contract(other, "INV999", total="5000")

    # Owner's totals must not include the other user's contract.
    assert harness.financial.get_total_expected_return(owner) == Decimal("1000")
