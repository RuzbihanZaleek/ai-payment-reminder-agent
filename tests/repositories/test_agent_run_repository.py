from app.models.agent_run import AgentRun
from app.enums.agent_run_status import AgentRunStatus
from app.repositories.agent_run_repository import AgentRunRepository


def test_create_agent_run(db_session):

    repository = AgentRunRepository(db_session)

    agent_run = AgentRun(
        contract_id=1,
        message_id="msg_123",
        status=AgentRunStatus.PENDING,
    )

    created_run = repository.create(agent_run)

    assert created_run.id is not None
    assert created_run.status == AgentRunStatus.PENDING
    assert created_run.message_id == "msg_123"


def test_get_agent_run_by_id(db_session):

    repository = AgentRunRepository(db_session)

    agent_run = AgentRun(
        contract_id=1,
        message_id="msg_456",
        status=AgentRunStatus.RUNNING,
        current_step="ConfidenceChecker",
    )

    created_run = repository.create(agent_run)

    fetched_run = repository.get_by_id(
        created_run.id
    )

    assert fetched_run is not None
    assert fetched_run.id == created_run.id
    assert fetched_run.status == AgentRunStatus.RUNNING
    assert fetched_run.current_step == "ConfidenceChecker"


def test_get_all_agent_runs(db_session):

    repository = AgentRunRepository(db_session)

    run1 = AgentRun(
        contract_id=1,
        message_id="msg_1",
        status=AgentRunStatus.PENDING,
    )

    run2 = AgentRun(
        contract_id=1,
        message_id="msg_2",
        status=AgentRunStatus.COMPLETED,
    )

    repository.create(run1)
    repository.create(run2)

    runs = repository.get_all()

    assert len(runs) >= 2


def test_update_agent_run_status(db_session):

    repository = AgentRunRepository(db_session)

    agent_run = AgentRun(
        contract_id=1,
        message_id="msg_789",
        status=AgentRunStatus.PENDING,
    )

    created_run = repository.create(agent_run)

    created_run.status = AgentRunStatus.COMPLETED
    created_run.current_step = "NotificationNode"

    updated_run = repository.update(created_run)

    assert updated_run.status == AgentRunStatus.COMPLETED
    assert updated_run.current_step == "NotificationNode"

    refetched_run = repository.get_by_id(created_run.id)

    assert refetched_run.status == AgentRunStatus.COMPLETED
