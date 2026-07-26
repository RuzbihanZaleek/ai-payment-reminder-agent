from decimal import Decimal

from app.services.reminder_execution_service import ReminderExecutionService
from app.agents.state import AgentState
from app.enums.trigger_type import TriggerType


class FakeContract:

    def __init__(self):
        self.id = 5
        self.total_amount = Decimal("1000")
        self.daily_amount = Decimal("20")
        self.whatsapp_chat_id = "chat_555"


class FakeAgentRunRepository:

    def __init__(self):
        self._next_id = 1
        self.created = None

    def create(self, agent_run):

        agent_run.id = self._next_id
        self._next_id += 1
        self.created = agent_run

        return agent_run

    def update(self, agent_run):

        return agent_run


class FakePaymentService:

    def calculate_remaining_amount(self, total_amount, contract_id):

        return Decimal("850")


class FakeWorkflow:

    def __init__(self):
        self.called_with = None

    def process(self, state, agent_run_id):

        self.called_with = (state, agent_run_id)

        return state


def _service(workflow):

    return ReminderExecutionService(
        FakeAgentRunRepository(),
        workflow,
        FakePaymentService(),
    )


def test_reminder_execution_creates_correct_state():

    workflow = FakeWorkflow()
    service = _service(workflow)

    result = service.execute(FakeContract())

    assert workflow.called_with is not None

    state, agent_run_id = workflow.called_with

    assert isinstance(state, AgentState)
    assert state.contract_id == 5
    assert state.whatsapp_chat_id == "chat_555"
    assert state.total_amount == Decimal("1000")
    assert state.daily_amount == Decimal("20")
    assert state.remaining_amount == Decimal("850")
    assert agent_run_id == 1

    assert result is state


def test_trigger_type_is_scheduled_reminder():

    workflow = FakeWorkflow()
    service = _service(workflow)

    service.execute(FakeContract())

    state, _ = workflow.called_with

    assert state.trigger_type == TriggerType.SCHEDULED_REMINDER
