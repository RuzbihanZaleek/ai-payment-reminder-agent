"""Audit service + audit events emitted by auth / approval / contract flows."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.contract_service import ContractService
from app.services.payment_approval_service import PaymentApprovalService
from app.core.security import hash_password
from app.enums.payment_status import PaymentStatus
from app.enums.approval_status import ApprovalStatus
from app.schemas.contract import ContractCreate


class FakeAuditRepository:
    def __init__(self):
        self.records = []

    def create(self, audit_log):
        audit_log.id = len(self.records) + 1
        self.records.append(audit_log)
        return audit_log


def _audit():
    return AuditService(FakeAuditRepository())


# --- AuditService directly --------------------------------------------------

def test_record_persists_audit_log():
    repo = FakeAuditRepository()
    service = AuditService(repo)

    service.record(action="X", user_id=5, entity_type="thing", entity_id=9, metadata={"k": "v"})

    assert len(repo.records) == 1
    row = repo.records[0]
    assert row.action == "X"
    assert row.user_id == 5
    assert row.metadata_json == {"k": "v"}


# --- Auth events ------------------------------------------------------------

class FakeUserRepository:
    def __init__(self, existing=None):
        self.existing = existing

    def get_by_email(self, email):
        return self.existing

    def create(self, user):
        user.id = 1
        return user


def test_login_success_is_audited():
    audit = _audit()
    user = SimpleNamespace(id=7, hashed_password=hash_password("password123"))
    service = AuthService(FakeUserRepository(existing=user), audit_service=audit)

    service.authenticate("a@b.com", "password123")

    actions = [r.action for r in audit.repository.records]
    assert AuditService.USER_LOGIN in actions


def test_login_failure_is_audited_without_password():
    audit = _audit()
    user = SimpleNamespace(id=7, hashed_password=hash_password("correct"))
    service = AuthService(FakeUserRepository(existing=user), audit_service=audit)

    service.authenticate("a@b.com", "WRONGpassword")

    row = audit.repository.records[-1]
    assert row.action == AuditService.USER_LOGIN_FAILED
    assert row.metadata_json["reason"] == "invalid_password"
    # The password must never be stored.
    assert "WRONGpassword" not in str(row.metadata_json)


# --- Approval events --------------------------------------------------------

class FakePaymentRepo:
    def __init__(self, payment):
        self.payment = payment

    def get_by_id(self, payment_id):
        return self.payment

    def update(self, payment):
        return payment


class FakeContractRepo:
    def get_by_id(self, contract_id):
        return SimpleNamespace(user_id=1)


def _pending_payment():
    from app.models.payment import Payment

    return Payment(
        id=1,
        contract_id=1,
        amount=Decimal("50"),
        payment_date=date.today(),
        status=PaymentStatus.PENDING,
        approval_status=ApprovalStatus.PENDING,
        requires_manual_review=True,
    )


def test_payment_approval_is_audited():
    audit = _audit()
    service = PaymentApprovalService(
        FakePaymentRepo(_pending_payment()), FakeContractRepo(), audit_service=audit
    )

    service.approve_payment(payment_id=1, approved_by="boss", user_id=1)

    row = audit.repository.records[-1]
    assert row.action == AuditService.PAYMENT_APPROVED
    assert row.entity_id == 1


def test_payment_rejection_is_audited():
    audit = _audit()
    service = PaymentApprovalService(
        FakePaymentRepo(_pending_payment()), FakeContractRepo(), audit_service=audit
    )

    service.reject_payment(payment_id=1, rejected_by="boss", user_id=1)

    row = audit.repository.records[-1]
    assert row.action == AuditService.PAYMENT_REJECTED


# --- Contract creation ------------------------------------------------------

class FakeContractRepository:
    def create(self, contract):
        contract.id = 55
        return contract


def test_contract_creation_is_audited():
    audit = _audit()
    service = ContractService(FakeContractRepository(), audit_service=audit)

    data = ContractCreate(
        reference_code="INV-AUDIT",
        name="Audit Contract",
        total_amount=Decimal("1000"),
        daily_amount=Decimal("10"),
        start_date=date.today(),
        whatsapp_chat_id="chat",
    )

    service.create_contract(data, user_id=3)

    row = audit.repository.records[-1]
    assert row.action == AuditService.CONTRACT_CREATED
    assert row.entity_id == 55
    assert row.user_id == 3
