import pytest

from app.services.agent_execution_service import AgentExecutionService
from app.agents.state import AgentState
from app.enums.agent_run_status import AgentRunStatus


class FakeAgentRunRepository:

    def __init__(self):
        self.created = None
        self.status_history = []
        self._next_id = 1

    def create(self, agent_run):

        agent_run.id = self._next_id
        self._next_id += 1

        self.created = agent_run
        self.status_history.append(agent_run.status)

        return agent_run

    def update(self, agent_run):

        self.status_history.append(agent_run.status)

        return agent_run


class FakeWorkflow:

    def __init__(self):
        self.called_with = None

    def process(self, state, agent_run_id):

        self.called_with = (state, agent_run_id)
        state.payment_id = 99

        return state


class FakeFailingWorkflow:

    def __init__(self):
        self.called_with = None

    def process(self, state, agent_run_id):

        self.called_with = (state, agent_run_id)

        raise ValueError("workflow blew up")


def test_creates_agent_run():

    repo = FakeAgentRunRepository()
    workflow = FakeWorkflow()

    service = AgentExecutionService(repo, workflow)

    service.execute(
        contract_id=1,
        message_id="msg_1",
        message="I paid 100",
    )

    assert repo.created is not None
    assert repo.created.contract_id == 1
    assert repo.created.message_id == "msg_1"

    # PENDING at creation, then RUNNING before the workflow starts
    assert repo.status_history[0] == AgentRunStatus.PENDING
    assert repo.status_history[1] == AgentRunStatus.RUNNING


def test_starts_workflow():

    repo = FakeAgentRunRepository()
    workflow = FakeWorkflow()

    service = AgentExecutionService(repo, workflow)

    service.execute(
        contract_id=1,
        message_id="msg_1",
        message="I paid 100",
    )

    assert workflow.called_with is not None

    state, agent_run_id = workflow.called_with

    # Initial state is hydrated from the call arguments
    assert isinstance(state, AgentState)
    assert state.message == "I paid 100"
    assert state.message_id == "msg_1"
    assert state.contract_id == 1
    assert state.pending_dates == []
    assert state.requires_approval is False

    # The workflow receives the persisted run id
    assert agent_run_id == repo.created.id


def test_returns_final_state():

    repo = FakeAgentRunRepository()
    workflow = FakeWorkflow()

    service = AgentExecutionService(repo, workflow)

    result = service.execute(
        contract_id=1,
        message_id="msg_1",
        message="I paid 100",
    )

    assert isinstance(result, AgentState)
    assert result.payment_id == 99


def test_handles_failure_and_marks_run_failed():

    repo = FakeAgentRunRepository()
    workflow = FakeFailingWorkflow()

    service = AgentExecutionService(repo, workflow)

    with pytest.raises(ValueError):
        service.execute(
            contract_id=1,
            message_id="msg_1",
            message="I paid 100",
        )

    # The run ends FAILED and the failure is timestamped
    assert repo.created.status == AgentRunStatus.FAILED
    assert repo.created.completed_at is not None
    assert repo.status_history[-1] == AgentRunStatus.FAILED
