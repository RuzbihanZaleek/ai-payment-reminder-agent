"""End-to-end manual approval workflow, standardized errors, and health probes."""

from decimal import Decimal

from app.enums.payment_status import PaymentStatus
from app.enums.approval_status import ApprovalStatus


def test_manual_approval_confirms_money_end_to_end(make_actor):
    alice = make_actor()
    contract = alice.create_contract("APPROVE-1", total_amount=Decimal("1000"))

    payment_id = alice.add_payment(
        contract,
        Decimal("60"),
        status=PaymentStatus.PENDING,
        approval_status=ApprovalStatus.PENDING,
        requires_manual_review=True,
    )

    # Before approval: pending payment is not confirmed money.
    before = alice.client.get("/dashboard/overview", headers=alice.headers).json()
    assert Decimal(str(before["payments"]["total_amount_received"])) == Decimal("0")
    assert before["payments"]["pending_review_count"] == 1

    approve = alice.client.post(
        f"/approvals/{payment_id}/approve",
        json={"reviewed_by": "boss"},
        headers=alice.headers,
    )
    assert approve.status_code == 200
    assert approve.json()["approval_status"] == "APPROVED"

    # After approval: the payment now counts as received and leaves the queue.
    after = alice.client.get("/dashboard/overview", headers=alice.headers).json()
    assert Decimal(str(after["payments"]["total_amount_received"])) == Decimal("60")
    assert after["payments"]["pending_review_count"] == 0


def test_reject_keeps_money_unconfirmed(make_actor):
    alice = make_actor()
    contract = alice.create_contract("REJECT-1")

    payment_id = alice.add_payment(
        contract,
        Decimal("60"),
        status=PaymentStatus.PENDING,
        approval_status=ApprovalStatus.PENDING,
        requires_manual_review=True,
    )

    reject = alice.client.post(
        f"/approvals/{payment_id}/reject",
        json={"reviewed_by": "boss"},
        headers=alice.headers,
    )
    assert reject.status_code == 200
    assert reject.json()["approval_status"] == "REJECTED"

    overview = alice.client.get("/dashboard/overview", headers=alice.headers).json()
    assert Decimal(str(overview["payments"]["total_amount_received"])) == Decimal("0")


def test_standardized_error_envelope_unauthorized(client):
    # No token -> standardized 401 envelope.
    response = client.get("/dashboard/overview")

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert "message" in body["error"]


def test_standardized_error_envelope_not_found(make_actor):
    alice = make_actor()

    response = alice.client.post(
        "/approvals/999999/approve",
        json={"reviewed_by": "boss"},
        headers=alice.headers,
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PAYMENT_NOT_FOUND"


def test_standardized_validation_error_envelope(make_actor):
    alice = make_actor()
    contract = alice.create_contract("VALIDATION-1")

    response = alice.client.post(
        f"/approvals/{contract}/approve",  # missing reviewed_by
        json={},
        headers=alice.headers,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_health_is_liveness_only(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_reports_dependency_checks(client):
    response = client.get("/ready")

    body = response.json()
    # Database is reachable (SQLite), so that check must pass regardless of the
    # optional third-party config present in the environment.
    assert body["checks"]["database"] is True
    assert set(body["checks"]) == {
        "database",
        "jwt_config",
        "openai_config",
        "whatsapp_config",
    }
