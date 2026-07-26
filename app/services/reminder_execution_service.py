from datetime import datetime, timezone

from app.agents.state import AgentState
from app.agents.payment_workflow import PaymentWorkflow
from app.enums.trigger_type import TriggerType
from app.enums.agent_run_status import AgentRunStatus
from app.models.agent_run import AgentRun
from app.models.contract import Contract
from app.repositories.agent_run_repository import AgentRunRepository
from app.services.payment_service import PaymentService


class ReminderExecutionService:

    def __init__(
        self,
        agent_run_repository: AgentRunRepository,
        payment_workflow: PaymentWorkflow,
        payment_service: PaymentService,
    ):
        self.agent_run_repository = agent_run_repository
        self.payment_workflow = payment_workflow
        self.payment_service = payment_service

    def execute(self, contract: Contract) -> AgentState:

        remaining_amount = self.payment_service.calculate_remaining_amount(
            contract.total_amount,
            contract.id,
        )

        agent_run = AgentRun(
            contract_id=contract.id,
            message_id=f"reminder:{contract.id}",
            status=AgentRunStatus.PENDING,
        )

        agent_run = self.agent_run_repository.create(agent_run)

        agent_run.status = AgentRunStatus.RUNNING
        self.agent_run_repository.update(agent_run)

        state = AgentState(
            trigger_type=TriggerType.SCHEDULED_REMINDER,
            message="",
            contract_id=contract.id,
            whatsapp_chat_id=contract.whatsapp_chat_id,
            total_amount=contract.total_amount,
            daily_amount=contract.daily_amount,
            remaining_amount=remaining_amount,
        )

        try:
            return self.payment_workflow.process(state, agent_run.id)
        except Exception:
            agent_run.status = AgentRunStatus.FAILED
            agent_run.completed_at = datetime.now(timezone.utc)
            self.agent_run_repository.update(agent_run)
            raise
