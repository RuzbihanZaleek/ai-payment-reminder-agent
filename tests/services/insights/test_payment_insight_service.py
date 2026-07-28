from decimal import Decimal


def test_payment_summary_extremes(harness):
    user = harness.user()
    c = harness.contract(user, "INV001")
    harness.payment(c.id, "100")
    harness.payment(c.id, "50")
    harness.payment(c.id, "300")

    summary = harness.payments.get_payment_summary(user)

    assert summary["payment_count"] == 3
    assert summary["total_amount"] == Decimal("450")
    assert summary["largest_payment"] == Decimal("300")
    assert summary["smallest_payment"] == Decimal("50")
    assert summary["average_payment"] == Decimal("150.00")


def test_only_approved_payments_counted(harness):
    from app.enums.payment_status import PaymentStatus
    from app.enums.approval_status import ApprovalStatus

    user = harness.user()
    c = harness.contract(user, "INV001")
    harness.payment(c.id, "100")
    harness.payment(c.id, "999", status=PaymentStatus.PENDING, approval=ApprovalStatus.PENDING)

    assert harness.payments.get_payment_summary(user)["payment_count"] == 1


def test_payment_trends_by_month(harness):
    user = harness.user()
    c = harness.contract(user, "INV001", start_days_ago=90)
    harness.payment(c.id, "100", days_ago=1)
    harness.payment(c.id, "200", days_ago=2)

    trends = harness.payments.get_payment_trends(user)

    assert sum(t["count"] for t in trends) == 2
    assert sum(t["total"] for t in trends) == Decimal("300")


def test_payment_consistency(harness):
    user = harness.user()
    c = harness.contract(user, "INV001", start_days_ago=10)
    # Payments on 3 distinct days across a 5-day span.
    harness.payment(c.id, "10", days_ago=0)
    harness.payment(c.id, "10", days_ago=2)
    harness.payment(c.id, "10", days_ago=4)

    consistency = harness.payments.get_payment_consistency(user)
    assert consistency["payment_days"] == 3
    assert consistency["span_days"] == 5
    assert consistency["consistency_score"] == round(3 / 5, 4)


def test_top_payers_ranked(harness):
    user = harness.user()
    a = harness.contract(user, "A", name="Alice")
    b = harness.contract(user, "B", name="Bob")
    harness.payment(a.id, "100")
    harness.payment(b.id, "500")

    top = harness.payments.get_top_payers(user, limit=2)
    assert [p["reference_code"] for p in top] == ["B", "A"]
    assert top[0]["total_paid"] == Decimal("500")


def test_empty_dataset(harness):
    user = harness.user()

    summary = harness.payments.get_payment_summary(user)
    assert summary["payment_count"] == 0
    assert summary["total_amount"] == Decimal("0")
    assert harness.payments.get_payment_streak(user) == {
        "longest_streak_days": 0,
        "current_streak_days": 0,
    }
