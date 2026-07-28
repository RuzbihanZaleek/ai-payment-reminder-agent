"""Financial tools: service delegation + tenant isolation."""

from decimal import Decimal
from types import SimpleNamespace

from app.models.contract import ContractStatus
from app.repositories.pagination import PageResult
from app.ai.tools import ContractTool, PaymentTool, ReceiptTool


def _contract(cid, user_id, name="John Payment", ref="INV001", status=ContractStatus.ACTIVE):
    return SimpleNamespace(
        id=cid,
        user_id=user_id,
        reference_code=ref,
        name=name,
        total_amount=Decimal("1100"),
        daily_amount=Decimal("10"),
        currency="USD",
        status=status,
    )


class FakeContractService:
    def __init__(self, contracts):
        self._contracts = contracts
        self.calls = []

    def get_user_contracts(self, user_id, status=None):
        self.calls.append((user_id, status))
        return [
            c for c in self._contracts
            if c.user_id == user_id and (status is None or c.status == status)
        ]

    def get_contract(self, contract_id):
        return next((c for c in self._contracts if c.id == contract_id), None)


class FakeContractReporting:
    def __init__(self, summary=None):
        self.summary = summary
        self.calls = []

    def get_contract_summary(self, contract_id, user_id):
        self.calls.append((contract_id, user_id))
        return self.summary


class FakePaymentService:
    def __init__(self, payments=None, total_paid=Decimal("0")):
        self._payments = payments or []
        self._total_paid = total_paid

    def get_contract_payments(self, contract_id):
        return self._payments

    def calculate_total_paid(self, contract_id):
        return self._total_paid


class FakeReceiptReporting:
    def __init__(self, receipts=None):
        self._receipts = receipts or []

    def get_receipt_history(self, contract_id, page, page_size, order):
        return PageResult(items=self._receipts, total=len(self._receipts))


# --- ContractTool -----------------------------------------------------------

def test_get_active_contracts_delegates_with_active_filter():
    svc = FakeContractService([_contract(1, 7), _contract(2, 7, status=ContractStatus.COMPLETED)])
    tool = ContractTool(svc, FakeContractReporting())

    result = tool.get_active_contracts(7)

    assert svc.calls == [(7, ContractStatus.ACTIVE)]
    assert [c["contract_id"] for c in result] == [1]
    assert result[0]["reference_code"] == "INV001"


def test_get_contract_summary_delegates_to_reporting():
    summary = {"contract_id": 1, "remaining_amount": Decimal("900")}
    tool = ContractTool(FakeContractService([]), FakeContractReporting(summary=summary))

    assert tool.get_contract_summary(1, 7) == summary


# --- PaymentTool: tenant isolation ------------------------------------------

def test_payment_history_returns_data_for_owner():
    payments = [SimpleNamespace(id=1, amount=Decimal("200"), payment_date="2026-01-01",
                                status=SimpleNamespace(value="APPROVED"),
                                approval_status=SimpleNamespace(value="APPROVED"))]
    contract = _contract(1, 7)
    tool = PaymentTool(FakePaymentService(payments), FakeContractService([contract]))

    result = tool.get_payment_history(1, user_id=7)

    assert len(result) == 1
    assert result[0]["amount"] == Decimal("200")


def test_payment_history_blocked_for_non_owner():
    contract = _contract(1, 7)  # owned by user 7
    tool = PaymentTool(FakePaymentService([SimpleNamespace(id=1)]), FakeContractService([contract]))

    # User 99 must get nothing.
    assert tool.get_payment_history(1, user_id=99) == []


def test_total_paid_blocked_for_non_owner():
    contract = _contract(1, 7)
    tool = PaymentTool(FakePaymentService(total_paid=Decimal("200")), FakeContractService([contract]))

    assert tool.get_total_paid(1, user_id=99) is None
    assert tool.get_total_paid(1, user_id=7) == Decimal("200")


# --- ReceiptTool: tenant isolation ------------------------------------------

def test_receipts_blocked_for_non_owner():
    contract = _contract(1, 7)
    receipts = [SimpleNamespace(id=1, amount=Decimal("20"), previous_balance=Decimal("920"),
                                new_balance=Decimal("900"), allocation_summary="INV001: $20",
                                created_at="2026-01-01")]
    tool = ReceiptTool(FakeReceiptReporting(receipts), FakeContractService([contract]))

    assert tool.get_latest_receipts(1, user_id=99) == []
    owned = tool.get_latest_receipts(1, user_id=7)
    assert len(owned) == 1
    assert owned[0]["new_balance"] == Decimal("900")
