from datetime import date

from app.models.contract import Contract
from app.models.scheduler_run import SchedulerRun
from app.models.scheduler_event import SchedulerEvent
from app.enums.scheduler_run_status import SchedulerRunStatus
from app.repositories.contract_repository import ContractRepository
from app.repositories.scheduler_run_repository import SchedulerRunRepository
from app.repositories.scheduler_event_repository import SchedulerEventRepository


def _seed_run_and_contract(db_session):

    # scheduler_events FKs both scheduler_runs and contracts, so both parents
    # must exist first.
    contract = ContractRepository(db_session).create(
        Contract(
            name="c",
            total_amount=1000,
            daily_amount=10,
            currency="USD",
            start_date=date.today(),
            whatsapp_chat_id="chat",
        )
    )

    run = SchedulerRunRepository(db_session).create(
        SchedulerRun(
            run_type="daily_reminders",
            status=SchedulerRunStatus.RUNNING,
        )
    )

    return run, contract


def test_create_scheduler_event(db_session):

    run, contract = _seed_run_and_contract(db_session)

    repository = SchedulerEventRepository(db_session)

    created = repository.create(
        SchedulerEvent(
            scheduler_run_id=run.id,
            contract_id=contract.id,
            status="SENT",
        )
    )

    assert created.id is not None
    assert created.scheduler_run_id == run.id
    assert created.contract_id == contract.id
    assert created.status == "SENT"
    assert created.created_at is not None


def test_create_failed_event_with_message(db_session):

    run, contract = _seed_run_and_contract(db_session)

    repository = SchedulerEventRepository(db_session)

    created = repository.create(
        SchedulerEvent(
            scheduler_run_id=run.id,
            contract_id=contract.id,
            status="FAILED",
            message="reminder failed",
        )
    )

    assert created.status == "FAILED"
    assert created.message == "reminder failed"