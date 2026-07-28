from app.models.contract import ContractStatus


def test_overdue_detection(harness):
    user = harness.user()
    # Started 100 days ago, daily 10 -> expected ~1000 by now, but only 100 paid.
    behind = harness.contract(user, "LATE", total="2000", daily="10", start_days_ago=100)
    harness.payment(behind.id, "100")
    # On schedule: started today, nothing expected yet.
    harness.contract(user, "OK", total="1000", daily="10", start_days_ago=0)

    overdue = harness.contracts.get_overdue_contracts(user)

    assert [c["reference_code"] for c in overdue] == ["LATE"]


def test_no_overdue_when_on_track(harness):
    user = harness.user()
    c = harness.contract(user, "OK", total="1000", daily="10", start_days_ago=10)
    harness.payment(c.id, "200")  # expected ~100 by now, paid 200 -> ahead

    assert harness.contracts.get_overdue_contracts(user) == []


def test_near_completion(harness):
    user = harness.user()
    # remaining 50 of 1000 = 5% <= 10% -> near completion.
    c = harness.contract(user, "ALMOST", total="1000", daily="10")
    harness.payment(c.id, "950")

    near = harness.contracts.get_contracts_near_completion(user)
    assert [c["reference_code"] for c in near] == ["ALMOST"]


def test_completion_rate_and_distribution(harness):
    user = harness.user()
    harness.contract(user, "A", status=ContractStatus.ACTIVE)
    harness.contract(user, "B", status=ContractStatus.COMPLETED)
    harness.contract(user, "C", status=ContractStatus.COMPLETED)

    assert harness.contracts.get_contract_completion_rate(user) == round(2 / 3, 4)
    assert harness.contracts.get_contract_distribution(user) == {"ACTIVE": 1, "COMPLETED": 2}


def test_highest_and_lowest_balance(harness):
    user = harness.user()
    big = harness.contract(user, "BIG", total="1000")
    small = harness.contract(user, "SMALL", total="200")
    harness.payment(small.id, "100")  # remaining 100

    highest = harness.contracts.get_highest_balance_contracts(user, limit=1)
    lowest = harness.contracts.get_lowest_balance_contracts(user, limit=1)

    assert highest[0]["reference_code"] == "BIG"      # remaining 1000
    assert lowest[0]["reference_code"] == "SMALL"     # remaining 100


def test_tenant_isolation(harness):
    owner = harness.user()
    other = harness.user()
    harness.contract(owner, "MINE")
    harness.contract(other, "THEIRS")

    summary = harness.contracts.get_contract_summary(owner)
    assert summary["total_contracts"] == 1
