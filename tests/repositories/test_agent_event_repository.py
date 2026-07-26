from app.models.agent_run import AgentRun
from app.models.agent_event import AgentEvent
from app.enums.agent_run_status import AgentRunStatus
from app.enums.agent_event_status import AgentEventStatus
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.agent_event_repository import AgentEventRepository


def _create_agent_run(db_session) -> AgentRun:

    # agent_events.agent_run_id is a FK -> agent_runs.id, so every event
    # needs a real parent run to satisfy the constraint.
    run = AgentRun(
        contract_id=1,
        message_id="msg_parent",
        status=AgentRunStatus.RUNNING,
    )

    return AgentRunRepository(db_session).create(run)


def test_create_event(db_session):

    run = _create_agent_run(db_session)

    repository = AgentEventRepository(db_session)

    event = AgentEvent(
        agent_run_id=run.id,
        node_name="PaymentMessageAgent",
        status=AgentEventStatus.STARTED,
    )

    created_event = repository.create(event)

    assert created_event.id is not None
    assert created_event.status == AgentEventStatus.STARTED
    assert created_event.node_name == "PaymentMessageAgent"


def test_get_event_by_id(db_session):

    run = _create_agent_run(db_session)

    repository = AgentEventRepository(db_session)

    event = AgentEvent(
        agent_run_id=run.id,
        node_name="ConfidenceChecker",
        status=AgentEventStatus.COMPLETED,
        message="confidence ok",
    )

    created_event = repository.create(event)

    fetched_event = repository.get_by_id(
        created_event.id
    )

    assert fetched_event is not None
    assert fetched_event.id == created_event.id
    assert fetched_event.status == AgentEventStatus.COMPLETED
    assert fetched_event.message == "confidence ok"


def test_get_events_by_run_id(db_session):

    run = _create_agent_run(db_session)

    repository = AgentEventRepository(db_session)

    event1 = AgentEvent(
        agent_run_id=run.id,
        node_name="PaymentCreationNode",
        status=AgentEventStatus.STARTED,
    )

    event2 = AgentEvent(
        agent_run_id=run.id,
        node_name="PaymentCreationNode",
        status=AgentEventStatus.COMPLETED,
    )

    repository.create(event1)
    repository.create(event2)

    events = repository.get_by_run_id(
        run.id
    )

    assert len(events) >= 2
    assert all(event.agent_run_id == run.id for event in events)


def test_update_event_status(db_session):

    run = _create_agent_run(db_session)

    repository = AgentEventRepository(db_session)

    event = AgentEvent(
        agent_run_id=run.id,
        node_name="NotificationNode",
        status=AgentEventStatus.STARTED,
    )

    created_event = repository.create(event)

    created_event.status = AgentEventStatus.FAILED
    created_event.message = "delivery failed"

    updated_event = repository.update(created_event)

    assert updated_event.status == AgentEventStatus.FAILED
    assert updated_event.message == "delivery failed"

    refetched_event = repository.get_by_id(created_event.id)

    assert refetched_event.status == AgentEventStatus.FAILED
