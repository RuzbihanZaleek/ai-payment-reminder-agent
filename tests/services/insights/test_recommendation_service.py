def _joined(recs):
    return " ".join(recs)


def test_no_overdue_message(harness):
    user = harness.user()
    c = harness.contract(user, "OK", total="1000", daily="10", start_days_ago=5)
    harness.payment(c.id, "200")  # ahead of schedule

    recs = harness.recommendations.generate(user)
    assert "No contracts appear overdue." in recs


def test_near_completion_recommendation(harness):
    user = harness.user()
    c = harness.contract(user, "INV004", total="1000", daily="10")
    harness.payment(c.id, "980")  # remaining 20 -> near completion

    recs = harness.recommendations.generate(user)
    assert any("INV004" in r and "almost completed" in r for r in recs)


def test_strong_collection_rate_recommendation(harness):
    user = harness.user()
    c = harness.contract(user, "INV001", total="1000", daily="10")
    harness.payment(c.id, "950")  # 95% collected

    recs = harness.recommendations.generate(user)
    assert any("collection rate exceeds 90%" in r for r in recs)


def test_concentration_recommendation(harness):
    user = harness.user()
    # One dominant contract (>50% of active capital) + a small one.
    harness.contract(user, "BIG", total="5000", daily="10")
    harness.contract(user, "SMALL", total="200", daily="10")

    recs = harness.recommendations.generate(user)
    assert any("concentrated in one contract" in r for r in recs)


def test_overdue_followup_recommendation(harness):
    user = harness.user()
    c = harness.contract(user, "LATE", name="John", total="2000", daily="10", start_days_ago=100)
    harness.payment(c.id, "50")  # far behind schedule

    recs = harness.recommendations.generate(user)
    assert any("John" in r and "following up" in r.lower() for r in recs)
