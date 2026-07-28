"""ProactiveFinancialService detection + personalized recommendations.

Reuses the SQLite-backed insight harness (real services + seeded data).
"""


def test_detects_overdue(harness):
    user = harness.user()
    c = harness.contract(user, "LATE", total="2000", daily="10", start_days_ago=100)
    harness.payment(c.id, "100")  # far behind schedule

    analysis = harness.proactive.analyze(user)

    assert any("behind payment schedule" in r for r in analysis["risks"])
    assert any(s["type"] == "OVERDUE" for s in analysis["signals"])


def test_detects_low_collection(harness):
    user = harness.user()
    c = harness.contract(user, "INV001", total="1000", daily="10", start_days_ago=1)
    harness.payment(c.id, "100")  # 10% collected -> low

    analysis = harness.proactive.analyze(user)
    assert any("Collection performance is low" in r for r in analysis["risks"])


def test_detects_near_completion(harness):
    user = harness.user()
    c = harness.contract(user, "ALMOST", total="1000", daily="10", start_days_ago=1)
    harness.payment(c.id, "970")  # 30 remaining -> near completion

    analysis = harness.proactive.analyze(user)
    assert any("close to completion" in p for p in analysis["positives"])
    assert any(s["type"] == "NEAR_COMPLETION" for s in analysis["signals"])


def test_detects_inconsistent_payments(harness):
    user = harness.user()
    c = harness.contract(user, "INV001", total="5000", daily="10", start_days_ago=100)
    # Two payments 90 days apart -> very low consistency.
    harness.payment(c.id, "50", days_ago=0)
    harness.payment(c.id, "50", days_ago=90)

    analysis = harness.proactive.analyze(user)
    assert "Payment pattern is inconsistent" in analysis["risks"]


def test_healthy_portfolio_has_no_risks(harness):
    user = harness.user()
    c = harness.contract(user, "OK", total="1000", daily="10", start_days_ago=5)
    harness.payment(c.id, "950", days_ago=0)  # ahead + 95% collected

    analysis = harness.proactive.analyze(user)
    assert analysis["risks"] == []
    assert "healthy" in analysis["summary"]


def test_empty_portfolio(harness):
    user = harness.user()

    analysis = harness.proactive.analyze(user)
    assert analysis["risks"] == []
    assert "don't have any contracts" in analysis["summary"]


# --- personalized recommendations -------------------------------------------

def test_personalized_output_structure(harness):
    user = harness.user()
    good = harness.contract(user, "GOOD", total="1000", daily="10", start_days_ago=5)
    harness.payment(good.id, "950")
    late = harness.contract(user, "LATE", total="2000", daily="10", start_days_ago=100)
    harness.payment(late.id, "100")

    result = harness.recommendations.generate_personalized_recommendations(user)

    assert "summary" in result
    assert "financial_health" in result
    assert isinstance(result["positives"], list)
    assert isinstance(result["risks"], list)
    assert isinstance(result["suggestions"], list)
    # Overdue contract surfaced as a risk.
    assert any("behind" in r for r in result["risks"])


def test_personalized_empty_portfolio(harness):
    user = harness.user()

    result = harness.recommendations.generate_personalized_recommendations(user)
    assert result["risks"] == []
    assert result["financial_health"]["total_contracts"] == 0
