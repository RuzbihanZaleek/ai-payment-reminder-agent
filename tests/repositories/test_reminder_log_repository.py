import uuid
from datetime import date

from app.models.contract import Contract
from app.models.reminder_log import ReminderLog
from app.repositories.contract_repository import ContractRepository
from app.repositories.reminder_log_repository import ReminderLogRepository


def _create_contract(db_session) -> Contract:

    # reminder_logs.contract_id is a FK -> contracts.id, so every log needs a
    # real parent contract to satisfy the constraint.
    contract = Contract(
        reference_code=f"INV-{uuid.uuid4().hex[:12]}",
        name="c",
        total_amount=1000,
        daily_amount=10,
        currency="USD",
        start_date=date.today(),
        whatsapp_chat_id="chat",
    )

    return ContractRepository(db_session).create(contract)


def test_create_reminder_log(db_session):

    contract = _create_contract(db_session)

    repository = ReminderLogRepository(db_session)

    log = ReminderLog(
        contract_id=contract.id,
        message="Friendly reminder",
        status="SENT",
    )

    created = repository.create(log)

    assert created.id is not None
    assert created.contract_id == contract.id
    assert created.sent_at is not None


def test_has_sent_today_true_after_create(db_session):

    contract = _create_contract(db_session)

    repository = ReminderLogRepository(db_session)

    repository.create(
        ReminderLog(
            contract_id=contract.id,
            message="Friendly reminder",
            status="SENT",
        )
    )

    assert repository.has_sent_today(contract.id) is True


def test_has_sent_today_false_without_log(db_session):

    contract = _create_contract(db_session)

    repository = ReminderLogRepository(db_session)

    assert repository.has_sent_today(contract.id) is False
