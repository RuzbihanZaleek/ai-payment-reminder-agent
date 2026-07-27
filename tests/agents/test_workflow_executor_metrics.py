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

    def get_by_id(self, agent_run_id):

        return self.run

    def update(self, run):

        return run


class SlowNode:

    def execute(self, state):

        # Ensure a measurable, non-negative duration.
        import time
        time.sleep(0.005)

        return state


class FailingNode:

    def execute(self, state):

        import time
        time.sleep(0.005)

        raise ValueError("node blew up")


def _run():

    return AgentRun(
        contract_id=1,
        message_id="m",
        status=AgentRunStatus.RUNNING,
    )


def _event_by_status(events, status):

    return next(e for e in events if e.status == status)


def test_completed_event_has_duration():

    event_repo = FakeAgentEventRepository()
    run_repo = FakeAgentRunRepository(_run())

    executor = WorkflowExecutor(run_repo, event_repo)

    executor.execute_node(
        agent_run_id=1,
        node_name="SlowNode",
        node=SlowNode(),
        state=AgentState(message="x"),
    )

    completed = _event_by_status(event_repo.events, AgentEventStatus.COMPLETED)
    started = _event_by_status(event_repo.events, AgentEventStatus.STARTED)

    assert completed.duration_ms is not None
    assert completed.duration_ms >= 0

    # STARTED events are recorded before timing finishes -> no duration.
    assert started.duration_ms is None


def test_failed_event_has_duration():

    event_repo = FakeAgentEventRepository()
    run_repo = FakeAgentRunRepository(_run())

    executor = WorkflowExecutor(run_repo, event_repo)

    with pytest.raises(ValueError):
        executor.execute_node(
            agent_run_id=1,
            node_name="FailingNode",
            node=FailingNode(),
            state=AgentState(message="x"),
        )

    failed = _event_by_status(event_repo.events, AgentEventStatus.FAILED)

    assert failed.duration_ms is not None
    assert failed.duration_ms >= 0
    assert failed.message == "node blew up"
