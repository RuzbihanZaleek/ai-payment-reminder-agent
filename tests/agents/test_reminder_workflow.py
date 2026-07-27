from app.agents.reminder_workflow import ReminderWorkflow
from app.agents.state import AgentState
from app.enums.trigger_type import TriggerType


class FakeReminderDecisionNode:

    def execute(self, state):

        state.requires_approval = False

        return state


class FakeResponseGenerationNode:

    def execute(self, state):

        state.generated_message = "reminder text"

        return state


class FakeNotificationNode:

    def execute(self, state):

        state.notification_sent = True

        return state


class FakeWorkflowExecutor:

    def __init__(self):
        self.executed_nodes = []
        self.completed_run_id = None

    def execute_node(self, agent_run_id, node_name, node, state):

        self.executed_nodes.append(node_name)

        return node.execute(state)

    def mark_run_completed(self, agent_run_id):

        self.completed_run_id = agent_run_id


def _workflow(executor):

    return ReminderWorkflow(
        FakeReminderDecisionNode(),
        FakeResponseGenerationNode(),
        FakeNotificationNode(),
        executor,
    )


def test_executes_exactly_three_nodes():

    executor = FakeWorkflowExecutor()
    workflow = _workflow(executor)

    state = AgentState(
        trigger_type=TriggerType.SCHEDULED_REMINDER,
        message="",
    )

    workflow.process(state, agent_run_id=9)

    assert executor.executed_nodes == [
        "ReminderDecisionNode",
        "ResponseGenerationNode",
        "NotificationNode",
    ]


def test_marks_run_completed():

    executor = FakeWorkflowExecutor()
    workflow = _workflow(executor)

    state = AgentState(
        trigger_type=TriggerType.SCHEDULED_REMINDER,
        message="",
    )

    workflow.process(state, agent_run_id=9)

    assert executor.completed_run_id == 9


def test_propagates_state():

    executor = FakeWorkflowExecutor()
    workflow = _workflow(executor)

    state = AgentState(
        trigger_type=TriggerType.SCHEDULED_REMINDER,
        message="",
    )

    result = workflow.process(state, agent_run_id=9)

    assert result is state
    assert result.generated_message == "reminder text"
    assert result.notification_sent is True
