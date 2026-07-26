import pytest

from app.agents.workflow_executor import WorkflowExecutor
from app.agents.state import AgentState
from app.models.agent_run import AgentRun
from app.enums.agent_run_status import AgentRunStatus
from app.enums.agent_event_status import AgentEventStatus


class FakeAgentEventRepository:

    def __init__(self):
        self.events = []

    def create(self, event):

        self.events.append(event)

        return event


class FakeAgentRunRepository:

    def __init__(self, run):
        self.run = run
        self.updated = []

    def get_by_id(self, agent_run_id):

        return self.run

    def update(self, run):

        self.updated.append(run)

        return run


class FakeNode:

    def execute(self, state):

        state.payment_id = 1

        return state


class FakeFailingNode:

    def execute(self, state):

        raise ValueError("node blew up")


def make_run() -> AgentRun:

    return AgentRun(
        contract_id=1,
        message_id="msg_1",
        status=AgentRunStatus.RUNNING,
    )


def test_successful_execution_creates_started_and_completed_events():

    event_repo = FakeAgentEventRepository()
    run_repo = FakeAgentRunRepository(make_run())

    executor = WorkflowExecutor(run_repo, event_repo)

    state = AgentState(message="Paid 100")

    result = executor.execute_node(
        agent_run_id=7,
        node_name="PaymentCreationNode",
        node=FakeNode(),
        state=state,
    )

    # Node ran and returned the mutated state
    assert result.payment_id == 1

    # Exactly STARTED then COMPLETED, both tagged with run id + node name
    assert len(event_repo.events) == 2

    started, completed = event_repo.events

    assert started.status == AgentEventStatus.STARTED
    assert started.agent_run_id == 7
    assert started.node_name == "PaymentCreationNode"

    assert completed.status == AgentEventStatus.COMPLETED
    assert completed.agent_run_id == 7
    assert completed.node_name == "PaymentCreationNode"

    # A successful node must not touch the run status
    assert run_repo.updated == []


def test_failed_execution_creates_started_and_failed_events():

    event_repo = FakeAgentEventRepository()
    run_repo = FakeAgentRunRepository(make_run())

    executor = WorkflowExecutor(run_repo, event_repo)

    state = AgentState(message="Paid 100")

    with pytest.raises(ValueError):
        executor.execute_node(
            agent_run_id=7,
            node_name="PaymentCreationNode",
            node=FakeFailingNode(),
            state=state,
        )

    assert len(event_repo.events) == 2

    started, failed = event_repo.events

    assert started.status == AgentEventStatus.STARTED

    assert failed.status == AgentEventStatus.FAILED
    assert failed.node_name == "PaymentCreationNode"
    assert failed.message == "node blew up"


def test_failed_execution_updates_agent_run_status():

    event_repo = FakeAgentEventRepository()
    run = make_run()
    run_repo = FakeAgentRunRepository(run)

    executor = WorkflowExecutor(run_repo, event_repo)

    state = AgentState(message="Paid 100")

    with pytest.raises(ValueError):
        executor.execute_node(
            agent_run_id=7,
            node_name="PaymentCreationNode",
            node=FakeFailingNode(),
            state=state,
        )

    # The run was marked FAILED via the repository
    assert run.status == AgentRunStatus.FAILED
    assert run.completed_at is not None
    assert run_repo.updated == [run]
