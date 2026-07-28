"""ActionService: propose/confirm/cancel/expire, replay prevention, tenant isolation."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.base import Base
from app.models.pending_action import PendingAction
from app.repositories.pending_action_repository import PendingActionRepository
from app.ai.actions import ActionService, ActionType, PendingActionStatus


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


class FakeExecutor:
    def __init__(self, success=True):
        self.success = success
        self.calls = []

    def execute(self, pending_action):
        self.calls.append(pending_action.action_type)
        return {"success": self.success, "message": f"executed {pending_action.action_type}"}


class FakeApproval:
    def __init__(self, pendings=None):
        self._pendings = pendings or []

    def get_pending_approvals(self, user_id):
        return self._pendings


class FakeAudit:
    def __init__(self):
        self.records = []

    def record(self, action, **kwargs):
        self.records.append(action)

    def __getattr__(self, name):
        # Any AI_ACTION_* constant resolves to its own name.
        return name


def _service(session, executor=None, approval=None, audit=None, timeout=15):
    return ActionService(
        PendingActionRepository(session),
        executor or FakeExecutor(),
        approval or FakeApproval(),
        audit_service=audit,
        timeout_minutes=timeout,
    )


# --- propose ----------------------------------------------------------------

def test_propose_create_contract(session):
    audit = FakeAudit()
    service = _service(session, audit=audit)

    result = service.propose(7, ActionType.CREATE_CONTRACT, {
        "name": "John", "total_amount": 1200, "daily_amount": 20,
    })

    assert result["created"] is True
    assert "create this contract" in result["message"]
    pending = service.get_latest_pending(7)
    assert pending is not None
    assert pending.action_type == "CREATE_CONTRACT"
    assert "AI_ACTION_CREATED" in audit.records


def test_propose_create_contract_missing_params(session):
    service = _service(session)
    result = service.propose(7, ActionType.CREATE_CONTRACT, {"name": "John"})
    assert result["created"] is False
    assert service.get_latest_pending(7) is None


def test_propose_create_contract_invalid_amounts(session):
    service = _service(session)
    # daily > total violates the ContractCreate rule.
    result = service.propose(7, ActionType.CREATE_CONTRACT, {
        "name": "John", "total_amount": 100, "daily_amount": 200,
    })
    assert result["created"] is False
    assert service.get_latest_pending(7) is None


def test_propose_approve_single_pending(session):
    approval = FakeApproval([SimpleNamespace(id=5, amount=Decimal("100"))])
    service = _service(session, approval=approval)

    result = service.propose(7, ActionType.APPROVE_PAYMENT, {})

    assert result["created"] is True
    assert service.get_latest_pending(7).payload_json["payment_id"] == 5


def test_propose_approve_no_pending(session):
    service = _service(session, approval=FakeApproval([]))
    result = service.propose(7, ActionType.APPROVE_PAYMENT, {})
    assert result["created"] is False


def test_propose_send_reminders(session):
    service = _service(session)
    result = service.propose(7, ActionType.SEND_REMINDERS, {})
    assert result["created"] is True


# --- confirm / execute / replay ---------------------------------------------

def test_confirm_executes_once(session):
    executor = FakeExecutor(success=True)
    audit = FakeAudit()
    service = _service(session, executor=executor, audit=audit)
    service.propose(7, ActionType.SEND_REMINDERS, {})

    result = service.confirm_and_execute(7)

    assert result["success"] is True
    assert executor.calls == ["SEND_REMINDERS"]
    assert "AI_ACTION_EXECUTED" in audit.records
    # Marked EXECUTED.
    assert service.get_latest_pending(7) is None


def test_replay_prevention(session):
    executor = FakeExecutor(success=True)
    service = _service(session, executor=executor)
    service.propose(7, ActionType.SEND_REMINDERS, {})

    first = service.confirm_and_execute(7)
    second = service.confirm_and_execute(7)

    assert first["success"] is True
    assert second["success"] is False  # nothing left to confirm
    assert executor.calls == ["SEND_REMINDERS"]  # executed exactly once


def test_failed_execution_leaves_pending(session):
    executor = FakeExecutor(success=False)
    service = _service(session, executor=executor)
    service.propose(7, ActionType.SEND_REMINDERS, {})

    result = service.confirm_and_execute(7)

    assert result["success"] is False
    # Still pending so the user can retry.
    assert service.get_latest_pending(7) is not None


# --- cancel -----------------------------------------------------------------

def test_cancel(session):
    audit = FakeAudit()
    service = _service(session, audit=audit)
    service.propose(7, ActionType.SEND_REMINDERS, {})

    result = service.cancel_latest(7)

    assert result["message"] == "Action cancelled."
    assert service.get_latest_pending(7) is None
    assert "AI_ACTION_CANCELLED" in audit.records


def test_cancel_nothing(session):
    service = _service(session)
    assert service.cancel_latest(7)["success"] is False


# --- expire -----------------------------------------------------------------

def test_expire_stale(session):
    audit = FakeAudit()
    repo = PendingActionRepository(session)
    # Directly seed an already-expired pending action.
    repo.create(PendingAction(
        user_id=7, action_type="SEND_REMINDERS", payload_json={},
        status=PendingActionStatus.PENDING_CONFIRMATION.value,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    ))
    service = ActionService(repo, FakeExecutor(), FakeApproval(), audit_service=audit)

    count = service.expire_stale()

    assert count == 1
    assert service.get_latest_pending(7) is None
    assert "AI_ACTION_EXPIRED" in audit.records


def test_expired_action_not_confirmable(session):
    repo = PendingActionRepository(session)
    repo.create(PendingAction(
        user_id=7, action_type="SEND_REMINDERS", payload_json={},
        status=PendingActionStatus.PENDING_CONFIRMATION.value,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    ))
    service = _service(session)

    # Even before cleanup, an expired action is not returned for confirmation.
    assert service.get_latest_pending(7) is None
    assert service.confirm_and_execute(7)["success"] is False


# --- tenant isolation -------------------------------------------------------

def test_tenant_isolation(session):
    executor = FakeExecutor()
    service = _service(session, executor=executor)
    service.propose(7, ActionType.SEND_REMINDERS, {})

    # A different user cannot see or confirm user 7's pending action.
    assert service.get_latest_pending(99) is None
    assert service.confirm_and_execute(99)["success"] is False
    assert executor.calls == []
    # User 7's action is still pending.
    assert service.get_latest_pending(7) is not None
