"""End-to-end tenant isolation across reports, dashboard, analytics, approvals.

Two real users are registered and logged in; each sees only their own data
through genuine authenticated HTTP calls.
"""

from decimal import Decimal

from app.enums.approval_status import ApprovalStatus
from app.enums.payment_status import PaymentStatus


def test_reports_are_isolated_per_user(make_actor):
    alice = make_actor()
    bob = make_actor()

    contract_a = alice.create_contract("ALICE-1")
    alice.add_payment(contract_a, Decimal("100"))

    # Alice can read her own contract's payments.
    ok = alice.client.get(
        f"/reports/contracts/{contract_a}/payments", headers=alice.headers
    )
    assert ok.status_code == 200
    assert ok.json()["meta"]["total_items"] == 1

    # Bob cannot even see that Alice's contract exists -> 404 CONTRACT_NOT_FOUND.
    denied = bob.client.get(
        f"/reports/contracts/{contract_a}/payments", headers=bob.headers
    )
    assert denied.status_code == 404
    assert denied.json()["error"]["code"] == "CONTRACT_NOT_FOUND"


def test_dashboard_is_isolated_per_user(make_actor):
    alice = make_actor()
    bob = make_actor()

    contract_a = alice.create_contract("ALICE-D")
    alice.add_payment(contract_a, Decimal("250"))

    bob.create_contract("BOB-D")  # Bob has a contract but no payments.

    alice_view = alice.client.get("/dashboard/overview", headers=alice.headers).json()
    bob_view = bob.client.get("/dashboard/overview", headers=bob.headers).json()

    assert alice_view["contracts"]["total_contracts"] == 1
    assert Decimal(str(alice_view["payments"]["total_amount_received"])) == Decimal("250")

    assert bob_view["contracts"]["total_contracts"] == 1
    assert Decimal(str(bob_view["payments"]["total_amount_received"])) == Decimal("0")


def test_analytics_is_isolated_per_user(make_actor):
    alice = make_actor()
    bob = make_actor()

    contract_a = alice.create_contract("ALICE-AN", total_amount=Decimal("1000"))
    alice.add_payment(contract_a, Decimal("400"))

    alice_view = alice.client.get("/analytics/overview", headers=alice.headers).json()
    bob_view = bob.client.get("/analytics/overview", headers=bob.headers).json()

    assert Decimal(str(alice_view["payments"]["total_amount_received"])) == Decimal("400")
    assert Decimal(str(bob_view["payments"]["total_amount_received"])) == Decimal("0")


def test_pending_approvals_are_isolated_per_user(make_actor):
    alice = make_actor()
    bob = make_actor()

    contract_a = alice.create_contract("ALICE-AP")
    alice.add_payment(
        contract_a,
        Decimal("60"),
        status=PaymentStatus.PENDING,
        approval_status=ApprovalStatus.PENDING,
        requires_manual_review=True,
    )

    alice_pending = alice.client.get("/approvals/pending", headers=alice.headers).json()
    bob_pending = bob.client.get("/approvals/pending", headers=bob.headers).json()

    assert alice_pending["meta"]["total_items"] == 1
    assert bob_pending["meta"]["total_items"] == 0
