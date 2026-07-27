"""End-to-end pagination, filtering and ordering through the real API."""

from datetime import date
from decimal import Decimal

from app.enums.payment_status import PaymentStatus
from app.enums.approval_status import ApprovalStatus
from app.enums.agent_run_status import AgentRunStatus


def test_payment_pagination_metadata_and_paging(make_actor):
    alice = make_actor()
    contract = alice.create_contract("PAGE-1")

    for i in range(1, 26):  # 25 approved payments
        alice.add_payment(contract, Decimal(i))

    first = alice.client.get(
        f"/reports/contracts/{contract}/payments?page=1&page_size=10",
        headers=alice.headers,
    ).json()

    assert first["meta"] == {
        "total_items": 25,
        "total_pages": 3,
        "page": 1,
        "page_size": 10,
    }
    assert len(first["items"]) == 10

    last = alice.client.get(
        f"/reports/contracts/{contract}/payments?page=3&page_size=10",
        headers=alice.headers,
    ).json()
    assert len(last["items"]) == 5


def test_payment_filtering_by_status_and_amount(make_actor):
    alice = make_actor()
    contract = alice.create_contract("FILTER-1")

    alice.add_payment(contract, Decimal("50"), status=PaymentStatus.APPROVED,
                      approval_status=ApprovalStatus.APPROVED)
    alice.add_payment(contract, Decimal("500"), status=PaymentStatus.APPROVED,
                      approval_status=ApprovalStatus.APPROVED)
    alice.add_payment(contract, Decimal("70"), status=PaymentStatus.REJECTED,
                      approval_status=ApprovalStatus.REJECTED)

    approved = alice.client.get(
        f"/reports/contracts/{contract}/payments?status=APPROVED",
        headers=alice.headers,
    ).json()
    assert approved["meta"]["total_items"] == 2

    small = alice.client.get(
        f"/reports/contracts/{contract}/payments?max_amount=100",
        headers=alice.headers,
    ).json()
    returned = {Decimal(str(p["amount"])) for p in small["items"]}
    assert returned == {Decimal("50"), Decimal("70")}


def test_payment_ordering_newest_and_oldest_first(make_actor):
    alice = make_actor()
    contract = alice.create_contract("ORDER-1")

    first_id = alice.add_payment(contract, Decimal("10"))
    second_id = alice.add_payment(contract, Decimal("20"))

    desc = alice.client.get(
        f"/reports/contracts/{contract}/payments?order=desc",
        headers=alice.headers,
    ).json()["items"]
    assert [p["id"] for p in desc] == [second_id, first_id]

    asc = alice.client.get(
        f"/reports/contracts/{contract}/payments?order=asc",
        headers=alice.headers,
    ).json()["items"]
    assert [p["id"] for p in asc] == [first_id, second_id]


def test_payment_date_range_filter(make_actor):
    alice = make_actor()
    contract = alice.create_contract("DATERANGE-1")

    alice.add_payment(contract, Decimal("10"), payment_date=date(2026, 1, 10))
    alice.add_payment(contract, Decimal("20"), payment_date=date(2026, 6, 15))

    in_range = alice.client.get(
        f"/reports/contracts/{contract}/payments?date_from=2026-06-01&date_to=2026-06-30",
        headers=alice.headers,
    ).json()

    assert in_range["meta"]["total_items"] == 1
    assert Decimal(str(in_range["items"][0]["amount"])) == Decimal("20")


def test_agent_runs_pagination_and_status_filter(make_actor):
    alice = make_actor()
    contract = alice.create_contract("RUNS-1")

    alice.add_agent_run(contract, AgentRunStatus.COMPLETED)
    alice.add_agent_run(contract, AgentRunStatus.COMPLETED)
    alice.add_agent_run(contract, AgentRunStatus.FAILED)

    completed = alice.client.get(
        "/reports/agent-runs?status=COMPLETED",
        headers=alice.headers,
    ).json()
    assert completed["meta"]["total_items"] == 2

    page = alice.client.get(
        "/reports/agent-runs?page=1&page_size=2",
        headers=alice.headers,
    ).json()
    assert page["meta"]["total_items"] == 3
    assert page["meta"]["total_pages"] == 2
    assert len(page["items"]) == 2


def test_pagination_rejects_invalid_params(make_actor):
    alice = make_actor()
    contract = alice.create_contract("BADPAGE-1")

    too_small_page = alice.client.get(
        f"/reports/contracts/{contract}/payments?page=0",
        headers=alice.headers,
    )
    assert too_small_page.status_code == 422

    too_large_page_size = alice.client.get(
        f"/reports/contracts/{contract}/payments?page_size=1000",
        headers=alice.headers,
    )
    assert too_large_page_size.status_code == 422
